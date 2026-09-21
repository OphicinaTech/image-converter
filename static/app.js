const CONCURRENCY = 5;
const SUPPORTED_INPUT = [".png", ".webp", ".avif"];

const state = {
    directoryHandle: null,
    files: [],
    outputHandle: null,
    format: "webp",
    preset: "lossless",
};

const selectFolderButton = document.querySelector("#select-folder");
const convertButton = document.querySelector("#convert");
const folderTitle = document.querySelector("#folder-title");
const folderName = document.querySelector("#folder-name");
const statusElement = document.querySelector("#status");
const counterElement = document.querySelector("#counter");
const progressElement = document.querySelector("#progress");
const outputPathElement = document.querySelector("#output-path");
const errorsElement = document.querySelector("#errors");
const formatOptions = document.querySelectorAll(".format-option");
const presetOptions = document.querySelectorAll(".preset-option");

selectFolderButton.addEventListener("click", selectFolder);
convertButton.addEventListener("click", convertAll);
formatOptions.forEach(option => option.addEventListener("click", () => selectFormat(option)));
presetOptions.forEach(option => option.addEventListener("click", () => selectPreset(option)));

function selectFormat(option) {
    state.format = option.dataset.format;
    formatOptions.forEach(item => item.classList.toggle("selected", item === option));
}

function selectPreset(option) {
    state.preset = option.dataset.preset;
    presetOptions.forEach(item => item.classList.toggle("selected", item === option));
}

async function selectFolder() {
    if (!window.showDirectoryPicker) {
        setStatus("Seu navegador não suporta seleção de pasta com escrita local. Use Chrome ou Edge.");
        return;
    }

    try {
        state.directoryHandle = await window.showDirectoryPicker({ mode: "readwrite" });
        state.files = await collectImageFiles(state.directoryHandle);

        folderTitle.textContent = state.directoryHandle.name;
        folderName.textContent = state.files.length
            ? `${state.files.length} imagem(ns) encontrada(s) · PNG, WebP e AVIF`
            : "Nenhuma imagem PNG, WebP ou AVIF encontrada nesta pasta.";

        counterElement.textContent = `0 / ${state.files.length}`;
        convertButton.disabled = state.files.length === 0;
        outputPathElement.textContent = "—";
        errorsElement.textContent = "";
        resetProgress();

        setStatus(
            state.files.length
                ? "Pronto para iniciar a conversão."
                : "Nenhum arquivo compatível encontrado."
        );
    } catch (error) {
        if (error.name !== "AbortError") {
            setStatus(`Não foi possível selecionar a pasta: ${error.message}`);
        }
    }
}

function isSupportedInput(name) {
    const lower = name.toLowerCase();
    return SUPPORTED_INPUT.some(extension => lower.endsWith(extension));
}

async function collectImageFiles(directoryHandle, relativePath = "") {
    const files = [];

    for await (const [name, handle] of directoryHandle.entries()) {
        if (handle.kind === "directory") {
            if (name.toLowerCase() === "convertidas") continue;

            const nestedPath = relativePath ? `${relativePath}/${name}` : name;
            files.push(...await collectImageFiles(handle, nestedPath));
            continue;
        }

        if (isSupportedInput(name)) {
            const path = relativePath ? `${relativePath}/${name}` : name;
            files.push({ handle, relativePath: path });
        }
    }

    return files;
}

async function convertAll() {
    if (!state.directoryHandle || state.files.length === 0) return;

    setBusy(true);
    resetProgress();
    errorsElement.textContent = "";
    setStatus("Preparando conversão...");

    try {
        const timestamp = createTimestamp();
        const convertedRoot = await state.directoryHandle.getDirectoryHandle("convertidas", { create: true });
        state.outputHandle = await convertedRoot.getDirectoryHandle(timestamp, { create: true });

        outputPathElement.textContent = `convertidas/${timestamp}/`;
        await prepareOutputTree(state.outputHandle, state.files);

        let completed = 0;
        let failures = 0;
        let cursor = 0;
        const total = state.files.length;
        const workerCount = Math.min(CONCURRENCY, total);

        setStatus(`Convertendo em paralelo · até ${workerCount} ao mesmo tempo`);

        async function worker() {
            while (cursor < total) {
                const index = cursor++;
                const file = state.files[index];

                try {
                    const blob = await file.handle.getFile();
                    const result = await convertFile(blob, file.relativePath, state.format, state.preset);
                    await writeOutput(state.outputHandle, file.relativePath, state.format, result);
                } catch (error) {
                    failures++;
                    appendError(`${file.relativePath}: ${error.message}`);
                }

                completed++;
                updateProgress(completed, total);
                setStatus(`Convertendo em paralelo · ${completed} / ${total}`);
            }
        }

        await Promise.all(Array.from({ length: workerCount }, () => worker()));

        setStatus(
            failures === 0
                ? `Concluído · ${completed} arquivo(s) convertido(s).`
                : `Concluído com ${failures} erro(s) · ${completed - failures} convertido(s).`
        );
    } catch (error) {
        setStatus(`Erro durante a execução: ${error.message}`);
    } finally {
        setBusy(false);
    }
}

async function convertFile(blob, relativePath, format, preset) {
    const params = new URLSearchParams({
        output_format: format,
        preset,
    });

    const response = await fetch(`/api/convert?${params}`, {
        method: "POST",
        headers: {
            "Content-Type": blob.type || "application/octet-stream",
            "X-Relative-Path": relativePath,
        },
        body: blob,
    });

    if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
            const payload = await response.json();
            detail = payload.detail || detail;
        } catch (_) {
            // Keep HTTP status when the response is not JSON.
        }
        throw new Error(detail);
    }

    return response.blob();
}

async function prepareOutputTree(rootHandle, files) {
    const cache = new Map([["", rootHandle]]);
    const paths = new Set();

    for (const file of files) {
        const parts = file.relativePath.split("/");
        parts.pop();
        let current = "";
        for (const part of parts) {
            current = current ? `${current}/${part}` : part;
            paths.add(current);
        }
    }

    const ordered = [...paths].sort((a, b) => a.split("/").length - b.split("/").length);

    for (const relative of ordered) {
        const separator = relative.lastIndexOf("/");
        const parent = separator === -1 ? "" : relative.slice(0, separator);
        const name = separator === -1 ? relative : relative.slice(separator + 1);
        const parentHandle = cache.get(parent);
        cache.set(relative, await parentHandle.getDirectoryHandle(name, { create: true }));
    }
}

function outputFilename(relativePath, format) {
    return relativePath.replace(/\.(png|webp|avif)$/i, `.${format}`).split("/").pop();
}

async function writeOutput(rootHandle, relativePath, format, blob) {
    const parts = relativePath.split("/");
    parts.pop();
    let directory = rootHandle;

    for (const part of parts) {
        directory = await directory.getDirectoryHandle(part, { create: true });
    }

    const fileHandle = await directory.getFileHandle(outputFilename(relativePath, format), { create: true });
    const writable = await fileHandle.createWritable();

    try {
        await writable.write(blob);
        await writable.close();
    } catch (error) {
        await writable.abort();
        throw error;
    }
}

function createTimestamp() {
    const now = new Date();
    const pad = value => String(value).padStart(2, "0");

    return [now.getFullYear(), pad(now.getMonth() + 1), pad(now.getDate())].join("-")
        + "_"
        + [pad(now.getHours()), pad(now.getMinutes()), pad(now.getSeconds())].join("-");
}

function updateProgress(completed, total) {
    const percentage = total === 0 ? 0 : (completed / total) * 100;
    counterElement.textContent = `${completed} / ${total}`;
    progressElement.style.width = `${percentage}%`;
}

function resetProgress() {
    progressElement.style.width = "0%";
}

function setStatus(message) {
    statusElement.textContent = message;
}

function appendError(message) {
    errorsElement.textContent += `${message}\n`;
}

function setBusy(busy) {
    selectFolderButton.disabled = busy;
    convertButton.disabled = busy || state.files.length === 0;
    formatOptions.forEach(option => option.disabled = busy);
    presetOptions.forEach(option => option.disabled = busy);
    document.body.classList.toggle("is-busy", busy);
}
