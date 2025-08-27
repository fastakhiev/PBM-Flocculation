<template>
  <div class="charts-container">
    <div v-if="hasData" class="inner-container">
      <div class="chart-wrapper">
        <h4>α<sub>max</sub></h4>
        <Bar :data="alphaMaxChartData" :options="decimalCommaOptions" />
      </div>

      <div class="chart-wrapper">
        <h4>B</h4>
        <Bar :data="bChartData" :options="commonOptions" />
      </div>

      <div class="chart-wrapper">
        <h4>γ</h4>
        <Bar :data="gammaChartData" :options="decimalCommaOptions" />
      </div>
    </div>
    <div v-else class="no-data-message">
      <p>No data</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { Bar } from 'vue-chartjs';
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  BarElement,
  CategoryScale,
  LinearScale,
} from 'chart.js';

ChartJS.register(Title, Tooltip, BarElement, CategoryScale, LinearScale);

const props = defineProps({
  chartData: {
    type: Object,
    required: true,
    default: () => ({}),
  },
});

const hasData = computed(() => props.chartData && Object.keys(props.chartData).length > 0);

const processedData = computed(() => {
  if (!hasData.value) {
    return { labels: [], amax: [], b: [], gama: [] };
  }
  const sortedKeys = Object.keys(props.chartData).sort((a, b) => Number(a) - Number(b));
  
  const data = { labels: [], amax: [], b: [], gama: [] };
  
  for (const key of sortedKeys) {
    data.labels.push(key);
    data.amax.push(props.chartData[key].amax);
    data.b.push(props.chartData[key].b);
    data.gama.push(props.chartData[key].gama);
  }
  return data;
});

const createChartConfig = (data) => ({
  labels: processedData.value.labels,
  datasets: [{
    backgroundColor: '#3b82f6',
    data: data,
    borderRadius: 4,
    barPercentage: 0.7,
    categoryPercentage: 0.8,
  }],
});

const alphaMaxChartData = computed(() => createChartConfig(processedData.value.amax));
const bChartData = computed(() => createChartConfig(processedData.value.b));
const gammaChartData = computed(() => createChartConfig(processedData.value.gama));

const commonOptions = {
  responsive: true,
  maintainAspectRatio: false,
  layout: {
    padding: {
      bottom: 5, 
    }
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (context) => String(context.raw).replace('.', ','),
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { weight: '600', size: 14 } },
      title: {
        display: true,
        text: 'mg/g'
      }
    },
    y: {
      beginAtZero: true,
      grid: { color: '#e2e8f0' },
      title: {
        display: true,
        text: 'Value'
      }
    },
  },
};

const decimalCommaOptions = {
  ...commonOptions,
  scales: {
    ...commonOptions.scales,
    y: {
      ...commonOptions.scales.y,
      ticks: {
        callback: (value) => String(value).replace('.', ','),
      },
    },
  },
};
</script>

<style scoped>
.charts-container {
  width: 100%;
  height: 320px;
  margin-bottom: 35px;
}

.inner-container {
    display: flex;
    flex-direction: row;
    gap: 24px;
    width: 100%;
    height: 100%;
}

.chart-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
}

.chart-wrapper h4 {
  margin-bottom: 12px;
  font-weight: 600;
  color: #333;
  font-size: 1.1rem;
}


.no-data-message {
  text-align: center;
  color: #64748b;
  padding: 40px 0;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>