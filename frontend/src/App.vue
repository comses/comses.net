<template>
    <div>
        <c-header></c-header>
        <c-subheader :heading="$route.meta.heading" :subheading="$route.meta.subheading"></c-subheader>

        <section class="content-block container">
            <router-view></router-view>
        </section>
        <c-footer></c-footer>
    </div>
</template>

<script lang="ts">
    import Footer from './components/footer.vue'
    import Header from './components/header.vue'
    import SubHeader from './components/subheader.vue'
    export default {
        components: {
            'c-footer': Footer,
            'c-header': Header,
            'c-subheader': SubHeader
        }
    };


</script>

<style lang="scss">
</style>
