import { ApiRequest } from "../core.js";

export class PagesAPI {
    constructor(client) {
        this._client = client;
    }

    list() {
        return new ApiRequest(() =>
            this._client._request("GET", "/page/list")
        );
    }

    listMarkdown() {
        return new ApiRequest(() =>
            this._client._request("GET", "/page/list/markdown")
        );
    }
    listHtml() {
        return new ApiRequest(() =>
            this._client._request("GET", "/page/list/html")
        );
    }

    get(slug) {
        return new ApiRequest(() =>
            this._client._request("GET", `/page/${slug}`)
        );
    }

    create() {
        return new ApiRequest((data) =>
            this._client._request("POST", "/page/", { body: data })
        );
    }

    update() {
        return new ApiRequest((slug, data) =>
            this._client._request("PUT", `/page/${slug}`, { body: data })
        );
    }

    delete() {
        return new ApiRequest((slug) =>
            this._client._request("DELETE", `/page/${slug}`)
        );
    }

    // ✏️ Specialized updates

    updateMarkdown() {
        return new ApiRequest((slug, data) =>
            this._client._request("PUT", `/page/${slug}/markdown`, {
                body: data,
            })
        );
    }

    updateHTML() {
        return new ApiRequest((slug, data) =>
            this._client._request("PUT", `/page/${slug}/html`, {
                body: data,
            })
        );
    }
}
