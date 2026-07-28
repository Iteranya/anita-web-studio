import { ApiRequest } from "../core.js";

export class MediaAPI {
    constructor(client) { this._client = client; }

    list() {
        return new ApiRequest(() => this._client._request('GET', '/media/'));
    }

    upload() {
        return new ApiRequest((files) => {
            // files can be either: [File, File, ...] or a FormData
            const fd = files instanceof FormData ? files : new FormData();

            // If it's an array of files, append them
            if (Array.isArray(files)) {
                for (const f of files) fd.append('files', f);
            }

            return this._client._request('POST', '/media/', { body: fd });
        });
    }

    delete(f) {
        return new ApiRequest(() =>
            this._client._request('DELETE', `/media/${f}`)
        );
    }
}
