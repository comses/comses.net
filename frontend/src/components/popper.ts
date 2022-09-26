import {Component, Prop} from 'vue-property-decorator';
import Vue from 'vue';
import Popper from 'popper.js';

@Component
export default class MyPopper extends Vue {
    @Prop({default: 'bottom'})
    public placement: string;

    public isOpen = false;
    public triggerEl = null;
    public popperEl = null;

    public beforeDestroy() {
        if (!this.popper) return;
        this.popper.destroy();
    }

    public mounted() {
        this.triggerEl = this.$el.querySelector('[data-trigger]');
        this.popperEl = this.$el.querySelector('[data-popper]');
    }

    public open() {
        if (this.isOpen) return;
        this.isOpen = true;
        this.$nextTick(() => {
            this.setupPopper();
        });
    }

    public close() {
        if (!this.isOpen) return;
        this.isOpen = false;
    }

    public setupPopper() {
        if (!this.popper) {
            this.popper = new Popper(this.triggerEl, this.popperEl, {placement: this.placement});
        }
    }

    public render() {
        return this.$scopedSlots.default({
            isOpen: this.isOpen,
            open: this.open,
            close: this.close,
        });
    }
}