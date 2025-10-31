<template>
    <div class="wrapper">
        <h1>物價趨勢</h1>
        <div class="content">
            <div class="selects">
                <select v-model="prices.selectedCategory">
                    <option disabled value="">請選擇商品類別</option>
                    <option
                        v-for="category in categoryKeys"
                        :key="category"
                        :value="category"
                    >
                        {{ categoryName(category) }}
                    </option>
                </select>
                <select v-model="prices.selectedProduct">
                    <option disabled value="">請選擇商品</option>
                    <option
                        v-for="product in products"
                        :key="product.產品名稱"
                        :value="product"
                    >
                        {{ product.產品名稱 }}
                    </option>
                </select>
            </div>
            <div v-if="prices.selectedProduct" class="visualize">
                <TrendingChart
                    v-if="prices.selectedProduct"
                    :data="prices.selectedProduct"
                ></TrendingChart>
                <TrendingTable
                    v-if="prices.selectedProduct"
                    :data="prices.selectedProduct"
                ></TrendingTable>
            </div>
        </div>
    </div>
</template>

<script>
import { usePricesStore } from '@/stores/prices';
import Categories from '@/constants/categories';
import TrendingTable from '@/components/TrendingTable.vue';
import TrendingChart from '@/components/TrendingChart.vue';
import { ref, computed, onMounted, watch } from 'vue';

const prices = ref({
    selectedCategory: '',
    selectedProduct: '',
    productList: [],
});

const store = computed(() => {
    return usePricesStore();
});

const categoryKeys = computed(() => {
    return Object.keys(Categories);
});

const products = computed(() => {
    return prices.value.selectedCategory
        ? store.value.getPricesByCategory(prices.value.selectedCategory)
        : [];
});

const categoryName = (category) => {
    return Categories[category];
};

export default {
    components: {
        TrendingTable,
        TrendingChart,
    },
    setup() {
        onMounted(() => {
            const store = usePricesStore();
            store.fetchPrices();
        });
        watch(
            () => prices.value.selectedCategory,
            (newCategory) => {
                prices.value.selectedProduct = '';
                prices.value.productList = store.value.getPricesByCategory(
                    newCategory
                );
            }
        );
        watch(
            () => prices.value.selectedProduct,
            (newProduct) => {
                console.log(newProduct);
            }
        );
        return {
            prices,
            categoryKeys,
            products,
            categoryName,
        };
    }
};
</script>

<style scoped>
.wrapper {
    padding: 3em 5em;
    background: #f3f3f3;
    min-height: calc(100vh - 4.5em);
    height: calc(100% - 4.5em);
    box-sizing: border-box;
    width: 100%;
}

.content {
    margin-top: 2em;
    background-color: #fff;
    border-radius: 1em;
    padding: 2em;
    width: 100%;
}

.selects {
    display: flex;
    justify-content: flex-start;
    box-sizing: border-box;
}

.selects > select {
    padding: 0.5em;
    font-size: 1.1em;
    margin-right: 1em;
    border-radius: 0.5em;
    border: 1px solid #ccc;
    outline: none;
    cursor: pointer;
    appearance: auto !important;
    box-sizing: border-box;
    min-width: 0;
}

.visualize {
    display: flex;
    gap: 1em;
    box-sizing: border-box;
}

.visualize > * {
    flex: 1 1 50%;
    box-sizing: border-box;
    padding: 1em;
}

@media (max-width: 768px) {
    .selects {
        flex-direction: column;
        align-items: stretch;
    }

    .selects > select {
        width: 100%;
        margin-right: 0;
        margin-bottom: 0.8em;
    }

    .visualize {
        flex-direction: column;
    }

    .visualize > * {
        padding: 0.6em 0;
    }
}
</style>
