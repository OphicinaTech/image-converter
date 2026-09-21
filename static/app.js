const state = {
    directoryHandle: null,
    files: [],
    outputHandle: null,
    format: "webp",
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

const SUPPORTED_INPUT = ".png";

selectFolderButton.addEventListener("click", selectFolder);
convertButton.addEventListener("click", convertAll);
formatOptions.forEach(option => option.addEventListener("click", () => selectFormat(option)));

function selectFormat(option) {
    state.format = option.dataset.format;
    formatOptions.forEach(item => item.classList.toggle("selected", item === option));
}

async function selectFolder() {
    if (!window.showDirectoryPicker) {
        setStatus("Seu navegador não suporta seleção de pasta com escrita local. Use Chrome ou Edge.");
        return;
    }

    try {
        state.directoryHandle = await window.showDirectoryPicker({ mode: "readwrite" });
        state.files = await collectPngFiles(state.directoryHandle);

        folderTitle.textContent = state.directoryHandle.name;
        folderName.textContent = state.files.length
            ? `${state.files.length} PNG encontrado(s) · incluindo subpastas`
            : "Nenhum PNG encontrado nesta pasta.";

        counterElement.textContent = `0 / ${state.files.length}`;
        convertButton.disabled = state.files.length === 0;
        outputPathElement.textContent = "—";
        errorsElement.textContent = "";
        resetProgress();

        setStatus(
            state.files.length
                ? "Pronto para iniciar a conversão."
                : "Nenhum arquivo PNG encontrado."
        );
    } catch (error) {
        if (error.name !== "AbortError") {
            setStatus(`Não foi possível selecionar a pasta: ${error.message}`);
        }
    }
}

async function collectPngFiles(directoryHandle, relativePath = "") {
    const files = [];

    for await (const [name, handle] of directoryHandle.entries()) {
        if (handle.kind === "directory") {
            if (name.toLowerCase() === "convertidas") continue;

            const nestedPath = relativePath ? `${relativePath}/${name}` : name;
            files.push(...await collectPngFiles(handle, nestedPath));
            continue;
        }

        if (name.toLowerCase().endsWith(SUPPORTED_INPUT)) {
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

        let completed = 0;
        let failures = 0;

        for (const file of state.files) {
            try {
                const blob = await file.handle.getFile();
                const result = await convertFile(blob, file.relativePath, state.format);
                await writeOutput(state.outputHandle, file.relativePath, state.format, result);
            } catch (error) {
                failures++;
                appendError(`${file.relativePath}: ${error.message}`);
            }

            completed++;
            updateProgress(completed, state.files.length);
            setStatus(`Convertendo ${file.relativePath}`);
        }

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

async function convertFile(blob, relativePath, format) {
    const response = await fetch(`/api/convert?output_format=${encodeURIComponent(format)}`, {
        method: "POST",
        headers: {
            "Content-Type": blob.type || "image/png",
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

async function writeOutput(rootHandle, relativePath, format, blob) {
    const parts = relativePath.split("/");
    const filename = parts.pop().replace(/\.png$/i, `.${format}`);
    let directory = rootHandle;

    for (const part of parts) {
        directory = await directory.getDirectoryHandle(part, { create: true });
    }

    const fileHandle = await directory.getFileHandle(filename, { create: true });
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
    document.body.classList.toggle("is-busy", busy);
}
