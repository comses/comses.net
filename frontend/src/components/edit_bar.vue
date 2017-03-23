<template>
    <div>
        <a class="btn btn-primary" href=""></a>
        <button class="btn btn-primary" type="button" @click="delete"></button>
    </div>
</template>
<style>
    body{
        background-color:#ff0000;
    }
</style>
<script>
    import * as Vue from 'vue'
    import {Component, Prop} from 'vue-property-decorator'
    import

    class EditBar extends Vue {
        @Prop
        update_url: string;

        @Prop
        delete_url: string;

        delete() {

        }

    }

    export default{
        data(){
            return{
                msg:'hello vue'
            }
        },
        components:{
            'other-component':OtherComponent,
            HeaderComponent,
        }
    }
</script>
