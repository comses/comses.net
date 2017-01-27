<template>
    <div>
        <c-header></c-header>
        <section class="carousel">
            <div class="container">
                <div class="row">
                    <h1>{{ $route.meta.name }}</h1>
                </div>
            </div>
        </section>

        <section class="content-block container">
            <router-view></router-view>
        </section>
        <c-footer></c-footer>
    </div>
</template>

<script lang="ts">
    import Footer from './footer'
    import Header from './header'
    export default {
        components: {
            'c-footer': Footer,
            'c-header': Header
        }
    };


</script>

<style lang="scss">
    @import "style";

    .social-media {
        list-style: none;
        padding-left: 0;
        text-align: center;
    }

    .social-media li {
        display: inline-block;
        text-align: center;
    }

    .social-media a {
        font-size: 32px;
    }

    .social-media a .fa-stack {
        color: #6f717a;
    }

    .social-media a .fa-stack:hover {
        color: #7b7d87;
    }

    .organizations li {
        display: inline-block;
        margin-right: 10px;
        margin-left: 10px;
        margin-top: 10px;
    }
</style>
