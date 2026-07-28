// 1. Import Alpine and Plugins
import Alpine from 'https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/module.esm.js';
import sort from 'https://cdn.jsdelivr.net/npm/@alpinejs/sort@latest/dist/module.esm.js'; 
import ace from 'https://esm.sh/ace-builds@1.32.7/src-min-noconflict/ace';

// 3. Import Your Logic
import { HikarinApi } from '../hikarin/api/client.js';
import notificationsStore from '../hikarin/alpine/notifications.js';
import editorManager from './editorManager.js';

// ==========================================
// ACE CONFIGURATION & SERVICE
// ==========================================

// Critical: Tell Ace where to fetch workers/themes/modes dynamically
const ACE_CDN = "https://cdn.jsdelivr.net/npm/ace-builds@1.32.7/src-min-noconflict/";
ace.config.set('basePath', ACE_CDN);
ace.config.set('modePath', ACE_CDN);
ace.config.set('themePath', ACE_CDN);
ace.config.set('workerPath', ACE_CDN); // Add this too for syntax checking

// Global Helper to init editors cleanly in Alpine components
window.AceService = {
    init: (element, mode, value) => {
        const editor = ace.edit(element);
        editor.setTheme("ace/theme/tomorrow_night_eighties");
        editor.session.setMode(`ace/mode/${mode}`);
        editor.setShowPrintMargin(false);
        editor.setOptions({
            fontSize: "13px",
            fontFamily: "'JetBrains Mono', monospace",
            useSoftTabs: true,
            tabSize: 2,
            showLineNumbers: true,
        });
        editor.setValue(value || "", -1); // -1 moves cursor to start
        return editor;
    }
};

// ==========================================
// ALPINE SETUP
// ==========================================

const hikarinApi = new HikarinApi();

Alpine.plugin(sort);

Alpine.magic('api', () => hikarinApi);
Alpine.store('notifications', notificationsStore);
Alpine.store('ainaState', {
    isSaving: false
});
Alpine.data('editorManager', editorManager);
// Make Alpine global for debugging
window.Alpine = Alpine;

Alpine.start();

console.log("Hikarin JS: Started");