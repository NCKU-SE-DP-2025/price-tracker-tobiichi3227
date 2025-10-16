<template>
    <div class="trending-table">
        <table>
            <thead>
                <tr>
                    <th rowspan="2">年份</th>
                    <th v-for="month in months" :key="month">{{ month }}</th>
                </tr>
            </thead>
            <tbody>
                <template v-for="year in years" :key="year">
                    <tr>
                        <td>{{ year }}</td>
                        <template
                            v-for="(value, monthIndex) in getYearData(year)"
                            :key="year + '-month-' + monthIndex"
                        >
                            <td>{{ valueDisplay(value) }}</td>
                        </template>
                    </tr>
                </template>
            </tbody>
        </table>
    </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
const yearData = ref({});
const months = computed(() => {
    return [
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec',
    ];
});
const getYearData = (year) => {
    return yearData.value[year];
};
const processInitData = (data) => {
    const startMonth = new Date(data.時間起點).getMonth() + 1;
    const endMonth = new Date(data.時間終點).getMonth() + 1;
    const startYear = new Date(data.時間起點).getFullYear();
    const endYear = new Date(data.時間終點).getFullYear();
    yearData.value = {};
    for (let year = startYear; year <= endYear; year++) {
        let yearPrices = [];
        for (let month = 1; month <= 12; month++) {
            if (year === startYear && month < startMonth) {
                yearPrices.push('0');
            } else if (year === endYear && month > endMonth) {
                yearPrices.push('0');
            } else {
                yearPrices.push(
                    data.統計值.split(',')[
                        month + (year - startYear) * 12 - startMonth
                    ]
                );
            }
        }
        yearData.value[year] = yearPrices;
    }
};
const valueDisplay = (value) => {
    return value === '0' ? '-' : value;
};
export default {
    props: {
        data: {
            type: Object,
            required: true,
        },
    },
    setup(props) {
        watch(
            () => props.data,
            (newVal) => {
                if (newVal) {
                    processInitData(newVal);
                }
            },
            { deep: true }
        );
        onMounted(() => {
            if (props.data) {
                processInitData(props.data);
            }
        });
        const years = computed(() => {
            const startYear = new Date(props.data.時間起點).getFullYear();
            const endYear = new Date(props.data.時間終點).getFullYear();
            let years = [];
            for (let year = startYear; year <= endYear; year++) {
                years.push(year);
            }
            return years;
        });
        return {
            months,
            years,
            getYearData,
            valueDisplay,
        };
    },
};
</script>

<style scoped>
.trending-table {
    margin-top: 2em;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    border: 1px solid #ccc;
    padding: 0.5em;
    text-align: center;
}
</style>
