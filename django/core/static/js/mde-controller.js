/**
 * Controller for the EasyMDE Markdown editor, pulled from https://github.com/torchbox/wagtail-markdown/blob/c67c2b366f2b2a657fa5fa89d406f7293a834389/src/wagtailmarkdown/static/wagtailmarkdown/js/easymde-controller.js#L1
 */
class EasyMDEContainer extends window.StimulusModule.Controller {
    static values = { autodownload: Boolean};

    connect() {
        if (this.hasAutodownloadValue) {
            mdeAttach(this.element.id, this.autodownloadValue);
        }
        else {
            mdeAttach(this.element.id);
        }
    }
}

window.wagtail.app.register('mde-controller', EasyMDEContainer);