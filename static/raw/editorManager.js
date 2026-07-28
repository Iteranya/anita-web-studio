// editorManager.js
export default (slug, initialData = {}) => ({
    slug: slug,
    isProcessing: false,
    statusText: 'Ready',
    editor: null,
    
    // Layout State
    leftWidth: 50, // 50/50 split by default
    showPreview: true,
    dragType: null, // 'horizontal' only now

    // Default Template (Full HTML structure since it's a raw editor)
    defaults: {
        content: `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page Title</title>
    <!-- Example: CDN Tailwind -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #f3f4f6; }
    </style>
</head>
<body class="p-10">
    <h1 class="text-3xl font-bold text-blue-600">Raw HTML Editor</h1>
    <p class="mt-2 text-gray-600">Edit everything in one file.</p>
    
    <script>
        console.log("Ready");
    </script>
</body>
</html>`
    },
    ...initialData,

    // ==========================================
    // UI / LAYOUT
    // ==========================================

    togglePreview() {
        this.showPreview = !this.showPreview;
        if (this.showPreview && this.leftWidth > 90) {
            this.leftWidth = 50;
        }
    },

    startDrag(e) {
        this.dragType = 'horizontal';
        document.body.style.cursor = 'col-resize';
        // Prevent text selection during drag
        e.preventDefault(); 
    },

    stopDrag() {
        this.dragType = null;
        document.body.style.cursor = 'default';
    },

    handleDrag(e) {
        if (this.dragType !== 'horizontal') return;

        const container = this.$refs.workspaceContainer;
        if (!container) return;

        const containerRect = container.getBoundingClientRect();
        
        // Calculate percentage of total width
        let newWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
        
        // Constraints (10% to 90%)
        if (newWidth < 10) newWidth = 10;
        if (newWidth > 90) newWidth = 90;
        
        this.leftWidth = newWidth;
        
        // Trigger resize for Ace to recalculate layout
        if(this.editor) this.editor.resize();
    },

    // ==========================================
    // INITIALIZATION & SYNC
    // ==========================================

    async init() {
        // Initialize single ACE editor (HTML Mode)
        // Make sure your HTML has x-ref="mainEditor"
        this.editor = window.AceService.init(
            this.$refs.mainEditor, 
            'html', 
            this.defaults.content
        );

        // Bind resize observer to container to fix Ace layout issues
        new ResizeObserver(() => {
            this.editor.resize();
        }).observe(this.$refs.workspaceContainer);

        await this.fetchAndRender();
    },

    async fetchAndRender() {
        try {
            const response = await this.$api.aina.get(this.slug).execute();
            
            // Retrieve from custom.raw_builder.html
            const savedContent = response.custom?.raw_builder?.html;
            
            if (savedContent) {
                this.editor.setValue(savedContent, -1);
            }

            this.updatePreview();

        } catch (error) {
            console.error("Fetch error:", error);
            this.$store.notifications.add({ type: 'error', message: 'Failed to load content.' });
        }
    },

    /**
     * Saves the draft to custom.raw_builder.html
     * Does NOT update the public facing site (unless you deploy)
     */
    async syncAndRender() {
        this.isProcessing = true;
        this.statusText = 'Saving...';
        const content = this.editor.getValue();

        try {
            // Get current data to preserve other fields if necessary
            const currentData = await this.$api.aina.get(this.slug).execute();
            const rawBuilder = currentData.custom?.raw_builder || {};

            const payload = {
                custom: {
                    raw_builder: {
                        ...rawBuilder,
                        html: content // Saving to the requested path
                    }
                }
            };
            
            // Use the API to update the 'custom' metadata field
            await this.$api.aina.updateHTML().execute(this.slug, payload);
            
            this.updatePreview();
            this.statusText = 'Saved';

        } catch (e) {
            console.error("Sync error", e);
            this.statusText = 'Save Failed';
            this.$store.notifications.add({ type: 'error', message: 'Failed to save draft.' });
        } finally {
            this.isProcessing = false;
        }
    },

    updatePreview() {
        const content = this.editor.getValue();
        if (this.$refs.previewFrame) {
            // Direct injection since it is a raw editor
            this.$refs.previewFrame.srcdoc = content;
        }
    },

    // ==========================================
    // DEPLOYMENT
    // ==========================================

    /**
     * Pushes the current Editor content directly to the public URL.
     */
    async deployHtml() {
        this.isProcessing = true;
        this.statusText = 'Deploying...';

        try {
            const productionHtml = this.editor.getValue();

            // Direct update of the main HTML body
            await this.$api.aina.updateHTML().execute(this.slug, { 
                html: productionHtml 
            });
            
            this.$store.notifications.add({
                type: 'success',
                title: 'Deployed',
                message: 'Site updated successfully.'
            });
            this.statusText = 'Deployed';

        } catch (error) {
            console.error("Deploy error:", error);
            this.$store.notifications.add({ type: 'error', message: 'Deployment failed.' });
            this.statusText = 'Error';
        } finally {
            this.isProcessing = false;
        }
    },

    // ==========================================
    // UTILS
    // ==========================================

    async copyPrompt() {
        try {
            const content = this.editor.getValue();
            const prompt = `Current HTML/CSS/JS Code:\n\n${content}\n\nTask: [Describe your change]`;
            
            await navigator.clipboard.writeText(prompt);
            this.$store.notifications.add({ type: 'success', message: 'Prompt copied!' });
            
        } catch (err) {
            console.error('Failed to copy', err);
        }
    }
});