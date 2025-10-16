<template>
    <div class="wrapper">
        <h1>各類商品物價概覽</h1>
        <h3 v-if="!isLoading" class="subtitle">
            資料更新時間：{{ updateTime }}
        </h3>
        <div class="prices">
            <CategoryPrice
                class="category"
                v-for="category in categoryList"
                :key="category"
                :category="category"
                :isLoading="isLoading"
                :errorMessage="errorMessage"
                :priceData="getPriceData(category)"
            ></CategoryPrice>
        </div>
    </div>
</template>

<script>
import CategoryPrice from '@/components/CategoryPrice.vue';
import Categories from '@/constants/categories';
import { usePricesStore } from '@/stores/prices';
import { ref, computed, onMounted } from 'vue';

const prices = ref({});
const categoryList = computed(() => Object.keys(Categories));
const isLoading = computed(() => {
    const store = usePricesStore();
    return store.isLoading;
});
const errorMessage = computed(() => {
    const store = usePricesStore();
    return store.errorMessage;
});
const updateTime = computed(() => {
    const store = usePricesStore();
    return store.updatedTime;
});
const getPriceData = (category) => {
    const store = usePricesStore();
    return store.getPricesByCategory(category);
};


export default {
    name: 'PriceOverview',
    components: {
        CategoryPrice,
    },
    setup() {
        onMounted(() => {
            const store = usePricesStore();
            store.fetchPrices();
        });
        return {
            prices,
            categoryList,
            isLoading,
            errorMessage,
            updateTime,
            getPriceData,
        };
    },
};
</script>

<style scoped>
.wrapper {
    padding: 3em 5em;
    background: #f3f3f3;
    min-height: calc(100vh - 4.5em);
    height: calc(100% - 4.5em);
    box-sizing: border-box;
}
.prices {
    display: flex;
    justify-content: space-around;
    flex-wrap: wrap;
}
.category {
    margin: 1em;
    flex-grow: 1;
}
.subtitle {
    font-weight: normal;
    margin-top: 0.5em;
}
</style>
