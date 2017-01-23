<template>
    <div>
        <h1><router-link :to="{ name: 'job_list'}">Jobs</router-link></h1>
        <router-view></router-view>
    </div>
</template>

<script lang="ts">
export default {

};


</script>

<style>

</style>
