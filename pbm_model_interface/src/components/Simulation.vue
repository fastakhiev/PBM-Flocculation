<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, nextTick } from 'vue';
import axios from 'axios';
import ComparisonChart from './ComparisonChart.vue';
import HistogramChart from './HistogramChart.vue';
import type { ChartData } from 'chart.js';
import router from '../router';



let eventSource: EventSource | null = null;

const selectedFile = ref<File | null>(null);
const isDragging = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const isLoaded = ref(false);

const isLoading = ref(false);
const error = ref<string | null>(null);
const simulationResult = ref<any | null>(null);
const showSimulationData = ref(false);


const optimizationInfo = ref<any | null>(null);

const chartData1 = ref<ChartData<'line'> | null>(null);
const chartData2 = ref<ChartData<'line'> | null>(null);




watch(simulationResult, (newResult) => {
  if (newResult) {
    const predictionData1 = newResult.time.map((t: number, index: number) => ({
      x: t,
      y: newResult.VMD_corrected[index],
    }));

    const predictionData2 = newResult.time.map((t: number, index: number) => ({
      x: t,
      y: newResult.DF_corrected[index],
    }));


    const experimentalData1 = newResult.time_exp.map((t: number, index: number) => ({
      x: t,
      y: newResult.d43_exp[index],
    }));

    const experimentalData2 = newResult.time_exp.map((t: number, index: number) => ({
      x: t,
      y: newResult.df_exp[index],
    }));
    
    chartData1.value = {
      datasets: [
        {
          label: 'Predict',
          data: predictionData1,
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          pointRadius: 0,
          tension: 0.1,
        },
        {
          label: 'Experiment',
          data: experimentalData1,
          backgroundColor: 'rgba(255, 99, 132, 1)',
          borderColor: 'rgba(255, 99, 132, 1)',
          showLine: false,
          pointRadius: 5,
        },
      ],
    };

    chartData2.value = {
      datasets: [
        {
          label: 'Predict',
          data: predictionData2,
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          pointRadius: 0,
          tension: 0.1,
        },
        {
          label: 'Experiment',
          data: experimentalData2,
          backgroundColor: 'rgba(255, 99, 132, 1)',
          borderColor: 'rgba(255, 99, 132, 1)',
          showLine: false,
          pointRadius: 5,
        },
      ],
    };
  } else {
    chartData1.value = null;
    chartData2.value = null;
  }
});


onMounted(async () => {
  checkOptimization();
  await nextTick();
  const restoredFile = getFileFromLocalStorage();
  if (restoredFile) {
    handleFile(restoredFile);
  }
  isLoaded.value = true;
});

async function checkOptimization() {
  try {
    const response = await axios.get('api/check_optimization');
    if (response.data.response) {
      showSimulationData.value = true;
      optimizationInfo.value = response.data;
    }
  } catch (err) {
    console.error(err);
  }
}


function listenForSimulationUpdates(taskId: string) {

  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource(`/api/get_result_simulation/${taskId}`);

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Simulation progress:', data);

    if (data.status === 'completed') {
      isLoading.value = false;
      simulationResult.value = data.result;
      eventSource?.close();
      eventSource = null;
    } else if (data.status === 'failed') {
      isLoading.value = false;
      error.value = `Ошибка выполнения симуляции: ${data.error || 'Неизвестная ошибка'}`;
      eventSource?.close();
      eventSource = null;
    }
  };

  eventSource.onerror = () => {
    error.value = 'Произошла ошибка сетевого соединения с сервером.';
    isLoading.value = false;
    eventSource?.close();
    eventSource = null;
  };
}

function getFileFromLocalStorage(): File | null {
  const base64 = localStorage.getItem("uploadedFile");
  if (!base64) return null;

  const byteString = atob(base64.split(',')[1]);
  const mimeString = base64.split(',')[0].split(':')[1].split(';')[0];
  const ab = new ArrayBuffer(byteString.length);
  const ia = new Uint8Array(ab);
  for (let i = 0; i < byteString.length; i++) {
    ia[i] = byteString.charCodeAt(i);
  }
  const fileName = localStorage.getItem("fileName");
  return new File([ab], fileName!, { type: mimeString });
}


function handleFile(file: File | null) {
  if (file && file.type === 'text/csv') {
    selectedFile.value = file;
    error.value = null;
  } else if (file) {
    error.value = 'Пожалуйста, выберите файл в формате .csv';
    clearFile();
  }
}

function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement;
  handleFile(target.files?.[0] ?? null);
}

function handleDrop(event: DragEvent) {
  isDragging.value = false;
  handleFile(event.dataTransfer?.files[0] ?? null);
}

function clearFile() {
  selectedFile.value = null;
  localStorage.removeItem("uploadedFile");
  localStorage.removeItem("fileName");
  if (fileInput.value) {
    fileInput.value.value = '';
  }
}

async function backToOptimization() {
  router.push("/");
  
}

async function handleStopSimulation() {
  const taskId = localStorage.getItem('simulationTaskId');
  if (!taskId) return;

  try {
    await axios.delete(`/api/stop_task/${taskId}`);
    isLoading.value = false;
    eventSource?.close();
    eventSource = null; 
    error.value = 'You sopped simulation';
  } catch (err) {
    console.error("Failed to stop simulation:", err);
    error.value = 'Не удалось отправить команду на остановку симуляции.';
  }
}

async function handleStartSimulation() {
  if (!selectedFile.value) {
    error.value = 'Пожалуйста, выберите CSV файл для загрузки.';
    return;
  }
  isLoading.value = true;
  error.value = null;
  simulationResult.value = null;

  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }

  try {
    const formData = new FormData();
    formData.append('file', selectedFile.value);

    const response = await axios.post('/api/start_simulation', formData);

    const taskId = response.data;
    if (!taskId) throw new Error('Не удалось получить ID задачи от сервера.');

    localStorage.setItem('simulationTaskId', taskId);

    listenForSimulationUpdates(taskId);
  } catch (err: any) {
    console.log(err);
    error.value = err.response?.data?.detail || err.response?.data?.message || 'Не удалось запустить симуляцию.';
    isLoading.value = false;
  }
}

onUnmounted(() => {
  if (eventSource) {
    eventSource.close();
  }
});
</script>

<template>
  <div class="dashboard-layout">
    <aside class="controls-panel">
      <div class="panel-header">
        <h2>Simulation Controls</h2>
      
        
      </div>

      <form v-if="isLoaded" @submit.prevent="handleStartSimulation" class="task-form">
        <div class="form-group">
          <label>Upload Data File</label>
          <label
            for="file-upload"
            class="file-uploader"
            :class="{ 'is-dragging': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
          >
            <input 
              id="file-upload" 
              ref="fileInput" 
              type="file" 
              @change="handleFileUpload" 
              accept=".csv" 
              name="file.csv"
            />
            <div v-if="!selectedFile" class="uploader-content">
              <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"></path></svg>
              <p><strong>Drag & Drop</strong> or <strong>click to browse</strong></p>
            </div>
            <div v-else class="uploader-content file-info">
              <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"></path></svg>
              <span class="filename">{{ selectedFile.name }}</span>
              <button type="button" @click.prevent="clearFile" class="clear-button" title="Remove file">&times;</button>
            </div>
          </label>
        </div>

          <table class="result-table">
            <tbody>
              <tr>
                <td style="font-weight: bold;">Parametrs</td>
                <td style="font-weight: bold;">Values</td>
                <td style="font-weight: bold;">Units</td>
              </tr>
              <tr>
                <td>Maximum collision efficiency (α<sub>max</sub>)</td>
                <td>{{ optimizationInfo.amax.toFixed(2) }}</td>
                <td>-</td>
              </tr>
              <tr>
                <td>Fragmentation rate parameter (B)</td>
                <td>{{ optimizationInfo.b.toFixed(2) }}</td>
                <td>-</td>
              </tr>
              <tr>
                <td>Kinetic parameter for flocs re-structuring (&#947;)</td>
                <td>{{ optimizationInfo.gama.toFixed(2) }}</td>
                <td>-</td>
              </tr>
              <tr>
                <td>Optimization time</td>
                <td>{{ optimizationInfo.optimization_time.toFixed(2) }}</td>
                <td>s</td>
              </tr>
            </tbody>
          </table>
        
        <button type="submit" :disabled="isLoading || !selectedFile">
          {{ isLoading ? 'Processing...' : 'Start Simulation' }}
        </button>
        <button
        class="back-button"
        @click="backToOptimization"
        >
          Back to optimization
        </button>
      </form>
    </aside>

    <main class="main-content">
      <div v-if="!isLoading && !simulationResult && !error" class="initial-state">
        <h1>Simulation Dashboard</h1>
        <p>Please upload a data file and start the simulation to view the results.</p>
      </div>
      <div v-if="isLoading" class="loading-indicator">
        <div class="spinner"></div>
        <p>Simulation is in progress, please wait...</p>
        <div class="controls">
          <button @click="handleStopSimulation" class="control-button stop-button">
            Stop Simulation
          </button>
        </div>
      </div>
      <div v-if="error" class="error-message">
        <p><strong>An error occurred:</strong> {{ error }}</p>
      </div>
      <div v-show="simulationResult" class="results-dashboard">
        <div class="charts-grid">
          <div class="chart-card">
            <h3 class="chart-title">Scattering exponent (SE) vs Time</h3>
            <ComparisonChart v-if="chartData2" :chartData="chartData2"/>
          </div>
          <div class="chart-card">
            <h3 class="chart-title">d43 vs Time</h3>
             <ComparisonChart v-if="chartData1" :chart-data="chartData1" />
          </div>
          <div class="chart-card">
            <h3 class="chart-title"  v-if="showSimulationData">{{ "Optimum data for " + optimizationInfo.cpamm }}</h3>
             <HistogramChart v-if="showSimulationData" :chart-data="optimizationInfo.optimum_data" />
          </div>
          <div v-if="showSimulationData" class="chart-card">
            <h3 class="chart-title">Optimization data</h3>
               <table class="result-table">
                  <tbody>
                    <tr>
                      <td style="font-weight: bold;">Parametrs</td>
                      <td style="font-weight: bold;">Values</td>
                      <td style="font-weight: bold;">Units</td>
                    </tr>
                    <tr>
                      <td>C-PAM type</td>
                      <td>{{ optimizationInfo.cpamm }}</td>
                      <td>-</td>
                    </tr>
                    <tr>
                      <td>Flocculant dosage</td>
                      <td>{{ optimizationInfo.dosage }}</td>
                      <td>mg/g</td>
                    </tr>
                    <tr>
                      <td>Shear rate (G)</td>
                      <td>{{ optimizationInfo.g.toFixed(2) }}</td>
                      <td>s⁻¹</td>
                    </tr>
                    <tr>
                      <td>Primary particle diameter</td>
                      <td>{{ optimizationInfo.do.toFixed(2) }}</td>
                      <td>nm</td>
                    </tr>
                    <tr>
                      <td>Goodness of fit</td>
                      <td>{{ optimizationInfo.gof.toFixed(2) }}</td>
                      <td>%</td>
                    </tr>
                  </tbody>
                </table>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>

.dashboard-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.controls-panel {
  flex: 0 0 380px;
  background-color: #ffffff;
  padding: 2rem;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.05);
  z-index: 10;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.panel-header {
  border-bottom: 1px solid #eef0f2;
  padding-bottom: 1.5rem;
  margin-bottom: 1.5rem;
}

.panel-header h2 {
  text-align: center;
  margin: 0 0 1.5rem 0;
  color: #333;
}

.reset-button {
  width: 100%;
  padding: 12px;
  font-size: 0.95rem;
  font-weight: bold;
  background-color: #e74c3c; 
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.reset-button:hover:not(:disabled) {
  background-color: #a21010;
}
.reset-button:disabled {
  background-color: #adb5bd;
  cursor: not-allowed;
}


.task-form {
  display: flex;
  flex-direction: column;
  flex-grow: 1; 
}
.form-group {
  margin-bottom: 1.5rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
}
.main-content { flex: 1; padding: 2rem; overflow-y: auto; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.initial-state { text-align: center; color: #777; }
.initial-state h1 { color: #333; }
.results-dashboard { width: 100%; height: 100%; }
.charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1.5rem; }
.chart-card { background: #fff; padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05); display: flex; flex-direction: column; }
.chart-title { margin-top: 0; margin-bottom: 1rem; font-size: 1.1rem; color: #333; }
.graph-placeholder { width: 100%; flex-grow: 1; min-height: 300px; background-color: #f8f9fa; border: 1px dashed #ccc; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #aaa; font-style: italic; }
.graph-placeholder::before { content: 'Chart Area'; }
.file-uploader { display: block; padding: 2rem; border: 2px dashed #ccc; border-radius: 8px; cursor: pointer; text-align: center; color: #555; transition: all 0.2s ease-in-out; }
.file-uploader:hover, .file-uploader.is-dragging { border-color: #42b983; background-color: #f0fdf4; }
.file-uploader input[type="file"] { display: none; }
.uploader-content { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem; }
.file-uploader .icon { width: 48px; height: 48px; fill: #999; transition: fill 0.2s; }
.file-uploader:hover .icon, .file-uploader.is-dragging .icon { fill: #42b983; }
.file-uploader p { margin: 0; font-size: 0.9rem; }
.file-info { flex-direction: row; justify-content: space-between; width: 100%; }
.file-info .icon { width: 24px; height: 24px; fill: #42b983; }
.filename { font-weight: 600; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-grow: 1; text-align: left; margin: 0 1rem; }
.clear-button { background: #eee; border: none; border-radius: 50%; width: 24px; height: 24px; font-size: 16px; font-weight: bold; color: #555; cursor: pointer; line-height: 24px; }
.clear-button:hover { background: #e0e0e0; color: #111; }
button[type="submit"] { width: 100%; padding: 14px; font-size: 1rem; font-weight: bold; background-color: #42b983; color: white; border: none; border-radius: 8px; cursor: pointer; transition: background-color 0.2s; margin-top: auto; }
button:hover:not(:disabled) { background-color: #36a473; }
button:disabled { background-color: #a5d6c1; cursor: not-allowed; }
.loading-indicator, .error-message { width: 100%; max-width: 500px; text-align: center; padding: 2rem; border-radius: 12px; }
.error-message { color: #d32f2f; background: #ffebee; border: 1px solid #d32f2f; }
.spinner { border: 4px solid rgba(0,0,0,0.1); border-top: 4px solid #3498db; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 1.5rem; }
.loading-indicator .controls { margin-top: 1.5rem; }
.control-button { padding: 10px 20px; font-size: 0.9rem; font-weight: bold; color: white; border: none; border-radius: 8px; cursor: pointer; transition: background-color 0.2s, transform 0.1s; }
.control-button:hover { transform: translateY(-2px); }
.stop-button { background-color: #e74c3c; }
.stop-button:hover { background-color: #c0392b; }

.back-button {
  width: 100%;
  padding: 12px;
  margin-top: 10px;
  font-size: 0.95rem;
  font-weight: bold;
  background-color: #6c757d; 
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.back-button:hover:not(:disabled) {
  background-color: #5a6268;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}

.result-table td {
  border: 1px solid #ccc;
  padding: 6px 10px;
}


@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>