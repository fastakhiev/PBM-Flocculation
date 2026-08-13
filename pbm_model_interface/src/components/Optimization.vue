<script setup lang="ts">

import { onMounted, ref, computed, watch } from 'vue';
import axios from 'axios';
import router from '../router';


const showDeleteConfirmation = ref(false);


const field1 = ref('');
const field2 = ref('');
const field6 = ref('');
const cpammOptions = ref(['E3', 'E2', 'E1', 'E1+', 'E1++++', 'BHMW']);
const field3 = ref(cpammOptions.value[0]);
const optimizationAlgorithms = ref(['Differential Evolution Algorithm (DEA)', 'Genetic Algorithm (GA)']);
const field4 = ref(optimizationAlgorithms.value[0]);
const dosageOptions = ref(['2', '6', '8']);
const field5 = ref(dosageOptions.value[0]);
const showHint1 = ref(false);
const showHint2 = ref(false);




const fileInputInit = ref<HTMLInputElement | null>(null);
const fileInputExp = ref<HTMLInputElement | null>(null);
const selectedFileExp = ref<File | null>(null);
const isDraggingExp = ref(false);
const selectedFileInit = ref<File | null>(null);
const isDraggingInit = ref(false);

const showSimulationButton = ref(false);
const optimizationInfo = ref<any | null>(null);


const isLoading = ref(false);
const error = ref<string | null>(null);
const isPaused = ref(false);
const taskResult = ref<any | null>(null);

let eventSource: EventSource | null = null;

const elapsedTime = ref(0);
let timerInterval: number | null = null;


const formattedTime = computed(() => {
  const minutes = Math.floor(elapsedTime.value / 60);
  const seconds = elapsedTime.value % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
});

watch(field3, (newCpamm) => {
  switch(newCpamm) {
    case 'E3':
      dosageOptions.value = ['2', '6', '8'];
      field5.value = dosageOptions.value[0];
      break;
    case 'E2':
      dosageOptions.value = ['6', '8', '10'];
      field5.value = dosageOptions.value[0];
      break;
    case 'E1':
      dosageOptions.value = ['4', '6', '8'];
      field5.value = dosageOptions.value[0];
      break;
    case 'E1+':
      dosageOptions.value = ['8', '12'];
      field5.value = dosageOptions.value[0];
      break;
    case 'E1++++':
      dosageOptions.value = ['6', '8', '10'];
      field5.value = dosageOptions.value[0];
      break;
    case 'BHMW':
      dosageOptions.value = ['2', '6', '14'];
      field5.value = dosageOptions.value[0];
      break;
  }
})


function startTimer() {
  elapsedTime.value = 0;
  if (timerInterval) clearInterval(timerInterval); 
  timerInterval = window.setInterval(() => {
    elapsedTime.value++;
  }, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

onMounted(() => {
  checkOptimization();
})

async function checkOptimization() {
  try {
    const response = await axios.get('/api/check_optimization');
    if (response.data.response) {
      showSimulationButton.value = true;
      optimizationInfo.value = response.data;
    }
  } catch (err) {
    console.error(err);
  }
}


function handleFileExp(file: File | null) {
  if (file && file.name.toLowerCase().endsWith('.csv')) {
    selectedFileExp.value = file;
    error.value = null; 
  } else if (file) {
    error.value = 'Please, upload .csv file';
    clearFileExp();
  }
}

function handleFileInit(file: File | null) {
  if (file && file.name.toLowerCase().endsWith('.csv')) {
    selectedFileInit.value = file;
    error.value = null; 
  } else if (file) {
    error.value = 'Please, upload .csv file';
    clearFileInit();
  }
}


function handleFileUploadExp(event: Event) {
  const target = event.target as HTMLInputElement;
  handleFileExp(target.files?.[0] ?? null); 
}

function handleFileUploadInit(event: Event) {
  const target = event.target as HTMLInputElement;
  handleFileInit(target.files?.[0] ?? null);
}


function handleDropExp(event: DragEvent) {
  isDraggingExp.value = false;
  handleFileExp(event.dataTransfer?.files[0] ?? null);
}

function handleDropInit(event: DragEvent) {
  isDraggingInit.value = false;
  handleFileInit(event.dataTransfer?.files[0] ?? null);
}


function clearFileExp() {
  selectedFileExp.value = null;
  if (fileInputExp.value) {
    fileInputExp.value.value = '';
  }
}

function clearFileInit() {
  selectedFileInit.value = null;
  if (fileInputInit.value) {
    fileInputInit.value.value = '';
  }
}


function listenForTaskUpdates(taskId: string) {
  eventSource = new EventSource(`/api/get_result_optimization/${taskId}`);

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
    if (data.status === 'completed') {
      isLoading.value = false;
      isPaused.value = false;
      if (data.result?.success === false) {
        taskResult.value = null;
        error.value = data.result.message || 'Optimization failed.';
      } else {
        taskResult.value = data.result;
      }
      stopTimer();
      eventSource?.close();
    } else if (data.status === 'failed') {
      isLoading.value = false;
      isPaused.value = false;
      error.value = `Optimization failed: ${data.error || 'Unknown error'}`;
      stopTimer();
      eventSource?.close();
    } else if (data.status === 'cancelled') {
      isLoading.value = false;
      isPaused.value = false;
      error.value = 'Optimization was cancelled.';
      stopTimer();
      eventSource?.close();
    }
  };

  eventSource.onerror = () => {
    error.value = 'The connection to the local calculation service was lost.';
    isLoading.value = false;
    isPaused.value = false;
    stopTimer();
    eventSource?.close();
  };
}


async function saveResults() {
  const taskId = localStorage.getItem('taskId');
  await axios.post('/api/save_optimization_results', { task_id: taskId });
  await saveFileToLocalStorage(selectedFileExp.value!);
  await router.push("/simulation");
}

async function handleStop() {
  const taskId = localStorage.getItem('taskId');
  if (!taskId) return;
  
  try {
    await axios.delete(`/api/stop_task/${taskId}`,);
    isLoading.value = false;
    isPaused.value = false;
    stopTimer();
    eventSource?.close();
    error.value = 'Optimization was stopped.';
  } catch (err) {
    console.error("Failed to stop optimization:", err);
    error.value = 'Could not stop the optimization.';
  }
}

function simulationButton() {
  router.push("/simulation");
}


async function handleSubmit() {
  if (!selectedFileExp.value) {
    error.value = 'Select an experimental CSV file.';
    return;
  }
  if (!selectedFileInit.value) {
    error.value = 'Select an initial-moments CSV file.';
    return;
  }
  if (!field6.value || Number(field6.value) <= 0) {
    error.value = 'Enter a positive initial fractal dimension (DF₀).';
    return;
  }
  isLoading.value = true;
  error.value = null;
  taskResult.value = null;
  if (eventSource) eventSource.close();

  startTimer();

  try {
    const formData = new FormData();
    formData.append('file_exp', selectedFileExp.value);
    formData.append('file_init', selectedFileInit.value);
    formData.append('data', field1.value);
    formData.append('data', field2.value);
    formData.append('data', field3.value);
    formData.append('data', field4.value);
    formData.append('data', field5.value);
    formData.append('data', field6.value);

    const response = await axios.post('/api/start_optimize', formData);
    const taskId = response.data;
    localStorage.setItem('taskId', taskId);
    if (!taskId) throw new Error('The calculation service did not return a task ID.');
    
    listenForTaskUpdates(taskId);
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.response?.data?.message || 'Could not start optimization.';
    isLoading.value = false;
    stopTimer();
  }
}

function deleteOptimizationData() {
  showDeleteConfirmation.value = true;
}


async function confirmDelete() {
  try {
    await axios.delete('/api/delete_optimization_data');
    optimizationInfo.value = null;
    showSimulationButton.value = false;
  } catch (err: any) {
    console.error(err);
    error.value = "Could not clear the active result.";
  } finally {
    showDeleteConfirmation.value = false;
  }
}

function cancelDelete() {
  showDeleteConfirmation.value = false;
}

function saveFileToLocalStorage(file: File): Promise<void> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      localStorage.setItem("uploadedFile", reader.result as string);
      localStorage.setItem("fileName", file.name);
      resolve();
    };
    reader.onerror = () => reject(reader.error ?? new Error("Failed to read CSV file"));
    reader.readAsDataURL(file);
  });
}

function blockInvalidKeys1(e: KeyboardEvent) {
  if (['-', '+', 'e', 'E'].includes(e.key)) {
    e.preventDefault();
  }
}

function sanitizePositive1(e: Event) {
  const target = e.target as HTMLInputElement;
  const raw = target.value;

  if (raw === '') {
    field1.value = '';
    showHint1.value = false;
    return;
  }

  const num = Number(raw);

  if (!isFinite(num) || num <= 0) {
    field1.value = '';
    target.value = '';
    showHint1.value = true;
  } else {
    field1.value = num.toString();
    showHint1.value = false;
  }
}

function blockInvalidKeys2(e: KeyboardEvent) {
  if (['-', '+', 'e', 'E'].includes(e.key)) {
    e.preventDefault();
  }
}

function sanitizePositive2(e: Event) {
  const target = e.target as HTMLInputElement;
  const raw = target.value;

  if (raw === '') {
    field2.value = '';
    showHint2.value = false;
    return;
  }

  const num = Number(raw);

  if (!isFinite(num) || num <= 0) {
    field2.value = '';
    target.value = '';
    showHint2.value = true;
  } else {
    field2.value = num.toString();
    showHint2.value = false;
  }
}
</script>

<template>

  <div class="task-form-container">
    <h1>Optimize</h1>
    <form @submit.prevent="handleSubmit" class="task-form">

      <div class="form-group">
        <label for="field1">Shear rate (G) s⁻¹</label>
        <input id="field1" v-model="field1" min=1 type="number" step="any" placeholder="Enter the G" required @keydown="blockInvalidKeys1" @input="sanitizePositive1"/>
        <small v-if="showHint1" class="text-red-600">
       The value must be greater than 0
      </small>
      </div>
      <div class="form-group">
        <label for="field2">Primary particle diameter (d₀) nm</label>
        <input id="field2" v-model="field2" min=1 type="number" step="any" placeholder="Enter the d0" required @keydown="blockInvalidKeys2" @input="sanitizePositive2"/>
        <small v-if="showHint2" class="text-red-600">
       The value must be greater than 0
      </small>
      </div>
      <div class="form-group">
        <label for="field6">Initial fractal dimension (DF₀)</label>
        <input id="field6" v-model="field6" min="0.000001" type="number" step="any" placeholder="Enter the DF₀" required @keydown="blockInvalidKeys2"/>
      </div>
        <div class="form-group">
        <label for="field3">Cationic polyacrylamide (C-PAM) type</label>
        <div class="select-wrapper">
          <select id="field3" v-model="field3" required>
              <option v-for="option in cpammOptions" :key="option" :value="option">
                  {{ option }}
              </option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label for="field5">Flocculant dosage (mg/g)</label>
        <div class="select-wrapper">
          <select id="field5" v-model="field5" required>
              <option v-for="option in dosageOptions" :key="option" :value="option">
                  {{ option }}
              </option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label for="field4">Optimization algorithm</label>
         <div class="select-wrapper">
          <select id="field4" v-model="field4" required>
              <option v-for="option in optimizationAlgorithms" :key="option" :value="option">
                  {{ option }}
              </option>
          </select>
        </div>
      </div>
     <div class="form-group">
        <label>Upload initial EQMOM moments M0-M4 (.csv) file</label>

        <label
          for="file-upload-init"
          class="file-uploader"
          :class="{ 'is-dragging': isDraggingInit }"
          @dragover.prevent="isDraggingInit = true"
          @dragleave.prevent="isDraggingInit = false"
          @drop.prevent="handleDropInit"
        >

          <input 
            id="file-upload-init" 
            ref="fileInputInit" 
            type="file" 
            @change="handleFileUploadInit" 
            accept=".csv" 
            required 
          />


          <div v-if="!selectedFileInit" class="uploader-content">
             <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"></path></svg>
             <p><strong>Drag & Drop</strong> your file here or <strong>click to browse</strong></p>
          </div>
          
          <div v-else class="uploader-content file-info">
            <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"></path></svg>
            <span class="filename">{{ selectedFileInit.name }}</span>
            <button type="button" @click.prevent="clearFileInit" class="clear-button" title="Remove file">&times;</button>
          </div>
        </label>
      </div>
      

      <div class="form-group">
        <label>Upload experimental (.csv) file </label>

        <label
          for="file-upload-exp"
          class="file-uploader"
          :class="{ 'is-dragging': isDraggingExp }"
          @dragover.prevent="isDraggingExp = true"
          @dragleave.prevent="isDraggingExp = false"
          @drop.prevent="handleDropExp"
        >

          <input 
            id="file-upload-exp" 
            ref="fileInputExp" 
            type="file" 
            @change="handleFileUploadExp" 
            accept=".csv" 
            required 
          />


          <div v-if="!selectedFileExp" class="uploader-content">
             <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"></path></svg>
             <p><strong>Drag & Drop</strong> your file here or <strong>click to browse</strong></p>
          </div>
          
          <div v-else class="uploader-content file-info">
            <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"></path></svg>
            <span class="filename">{{ selectedFileExp.name }}</span>
            <button type="button" @click.prevent="clearFileExp" class="clear-button" title="Remove file">&times;</button>
          </div>
        </label>
      </div>
      
      
      <button type="submit" :disabled="isLoading || !selectedFileExp || !selectedFileInit">
        {{ isLoading ? 'Processing...' : 'Optimize' }}
      </button>
    </form>
    
    <div class="result-area">
      <div v-if="isLoading" class="loading-indicator">
        <div class="spinner"></div>
        <div class="timer-display">
        <p>Elapsed time:</p>
        <p class="timer">{{ formattedTime }}</p>
        </div>
        <p>{{ isPaused ? 'Paused...' : 'Processing, please wait...' }}</p>
         <div class="optimization-controls">
          <button @click="handleStop" class="control-button stop-button">
            Stop
          </button>
        </div>
      </div>
      
      <div v-if="error" class="error-message">
        <p><strong>Error:</strong> {{ error }}</p>
      </div>
      <div v-if="taskResult" class="task-result">
        <h2>Optimization result:</h2>

        <ul class="result-list">
            <li><span>amax </span><span>{{ taskResult.amax.toFixed(2) }}</span></li>
            <li><span>B </span><span>{{ taskResult.B.toFixed(1) }}</span></li>
            <li><span>gamma (min⁻¹)</span><span>{{ taskResult.gama.toFixed(2) }}</span></li>
            <li><span>DF₀</span><span>{{ taskResult.df0.toFixed(2) }}</span></li>
        </ul>
        <button @click="saveResults">
          {{ 'Save & simulate PBM' }}
        </button>
      </div>
<div v-if="showSimulationButton" class="optimization-info">
  <h2>You have this data from previous optimization:</h2>

  <table class="result-table">
    <tbody>
      <tr>
        <td style="font-weight: bold;">Parameters</td>
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
        <td>{{ optimizationInfo.b.toFixed(1) }}</td>
        <td>-</td>
      </tr>
      <tr>
        <td>Kinetic parameter for flocs re-structuring (&#947;)</td>
        <td>{{ optimizationInfo.gama.toFixed(2) }}</td>
        <td>min⁻¹</td>
      </tr>
      <tr>
        <td>Initial fractal dimension (DF<sub>0</sub>)</td>
        <td>{{ optimizationInfo.df0 != null ? optimizationInfo.df0.toFixed(2) : '-' }}</td>
        <td>-</td>
      </tr>
      <tr>
        <td>Optimization time</td>
        <td>{{ optimizationInfo.optimization_time.toFixed(2) }}</td>
        <td>s</td>
      </tr>
    </tbody>
  </table>

    <table class="result-table">
    <tbody>
      <tr>
        <td style="font-weight: bold;">Parameters</td>
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

  <div class="buttons">
    <button class="simulation-button" @click="simulationButton">
      Simulate PBM
    </button>
    <button class="delete-optimization-data-button" @click="deleteOptimizationData">
      Clear data
    </button>
  </div>
</div>

    </div>
      <div v-if="showDeleteConfirmation" class="modal-overlay">
      <div class="modal-content">
        <h3>Confirm clear</h3>
        <p>Clear the active optimization result? Its immutable reproducibility report will remain in the local audit database.</p>
        <div class="modal-actions">
          <button @click="cancelDelete" class="modal-button cancel">Cancel</button>
          <button @click="confirmDelete" class="modal-button confirm">Clear</button>
        </div>
      </div>
    </div>
  </div>
</template>



<style>
body {
  margin: 0; 
  background-color: #f0f2f5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
</style>


<style scoped>

.task-form-container {
  max-width: 500px;
  margin: 40px auto;
  padding: 2rem;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}
h1, h2 {
  text-align: center;
  color: #333;
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


.form-group input {
  width: 100%;
  padding: 12px 14px; 
  box-sizing: border-box;
  background-color: #f7f8fa;
  border: 1px solid #e1e4e8; 
  border-radius: 8px;
  font-size: 1rem; 
  color: #333;
  transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s;
}


.form-group input::placeholder {
  color: #999;
}


.form-group input:focus {
  outline: none; 
  background-color: #fff;
  border-color: #42b983; 
  box-shadow: 0 0 0 3px rgba(66, 185, 131, 0.2);
}



.file-uploader {
  display: block;
  padding: 2rem;
  border: 2px dashed #ccc;
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  color: #555;
  transition: all 0.2s ease-in-out;
}
.file-uploader:hover,
.file-uploader.is-dragging {
  border-color: #42b983;
  background-color: #f0fdf4;
}
.file-uploader input[type="file"] {
  display: none;
}
.uploader-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}
.file-uploader .icon {
  width: 48px;
  height: 48px;
  fill: #999;
  transition: fill 0.2s;
}
.file-uploader:hover .icon,
.file-uploader.is-dragging .icon {
  fill: #42b983;
}
.file-uploader p {
  margin: 0;
  font-size: 0.9rem;
}
.file-info {
  flex-direction: row;
  justify-content: space-between;
  width: 100%;
}
.file-info .icon {
  width: 24px;
  height: 24px;
  fill: #42b983;
}
.filename {
  font-weight: 600;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-grow: 1;
  text-align: left;
  margin: 0 1rem;
}
.clear-button {
  background: #eee;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  font-size: 16px;
  font-weight: bold;
  color: #555;
  cursor: pointer;
  line-height: 24px;
}
.clear-button:hover {
  background: #e0e0e0;
  color: #111;
}


button[type="submit"] {
  width: 100%;
  padding: 14px;
  font-size: 1rem;
  font-weight: bold;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}
button[type="submit"]:hover:not(:disabled) {
  background-color: #36a473;
}
button:disabled {
  background-color: #a5d6c1;
  cursor: not-allowed;
}


.result-area {
  margin-top: 2rem;
}
.error-message {
  color: #d32f2f;
  background: #ffebee;
  border: 1px solid #d32f2f;
  padding: 1rem;
  border-radius: 8px;
}
.task-result {
  background: #f8f8f8;
  padding: 1rem;
  border-radius: 8px;
}
.result-list {
  list-style: none;
  padding: 0;
}
.result-list li {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}
.result-list li span {
  font-weight: bold;
  color: #333;
}
.result-list li:last-child {
  border-bottom: none;
}

.task-result {
  text-align: center; 
}

.task-result button {
  width: 50%;
  padding: 14px;
  font-size: 1rem;
  font-weight: bold;
  background-color: #1395ec;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.task-result button:hover:not(:disabled) {
  background-color: #16384e;
}


.loading-indicator {
  text-align: center;
  padding: 1rem;
  color: #555;
}
.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

.optimization-controls {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1.5rem;
}

.control-button {
  padding: 10px 20px;
  font-size: 0.9rem;
  font-weight: bold;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s, transform 0.1s;
}

.control-button:hover {
  transform: translateY(-2px);
}

.pause-resume-button {
  background-color: #f39c12; 
}
.pause-resume-button:hover {
  background-color: #e67e22;
}

.stop-button {
  background-color: #e74c3c;
}
.stop-button:hover {
  background-color: #c0392b;
}

.simulation-button {
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
.simulation-button:hover {
  background-color: #5a6268;
}

.delete-optimization-data-button {
  width: 100%;
  padding: 12px;
  margin-top: 10px;
  font-size: 0.95rem;
  font-weight: bold;
  background-color: #e74c3c; 
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.delete-optimization-data-button:hover {
  background-color: #c0392b;
}


.optimization-info {
  background: #f8f8f8;
  padding: 1rem;
  border-radius: 8px;
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


.form-group input:focus,
.form-group select:focus {
  outline: none; 
  background-color: #fff;
  border-color: #42b983; 
  box-shadow: 0 0 0 3px rgba(66, 185, 131, 0.2);
}

.form-group input,
.form-group select {
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  width: 100%;
  padding: 12px 14px; 
  box-sizing: border-box;
  background-color: #f7f8fa;
  border: 1px solid #e3e5b2; 
  border-radius: 8px;
  font-size: 1rem; 
  color: #333;
  transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s;
  padding-right: 40px; 
  cursor: pointer;
}

select::-ms-expand {
    display: none;
}

.timer-display {
  margin-bottom: 1rem;
  color: #333;
}

.timer-display p {
  margin: 0;
  line-height: 1.2;
}

.timer-display .timer {
  font-size: 2rem;
  font-weight: 600;
  font-family: 'Courier New', Courier, monospace;
  color: #3498db;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
  width: 90%;
  max-width: 400px;
  text-align: center;
}

.modal-content h3 {
  margin-top: 0;
  color: #333;
}

.modal-content p {
  margin-bottom: 2rem;
  color: #555;
}

.modal-actions {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.modal-button {
  flex-grow: 1;
  padding: 12px;
  border-radius: 8px;
  border: none;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.2s;
}

.modal-button.cancel {
  background-color: #f0f2f5;
  color: #333;
  border: 1px solid #e1e4e8;
}

.modal-button.cancel:hover {
  background-color: #e1e4e8;
}

.modal-button.confirm {
  background-color: #e74c3c;
  color: white;
}

.modal-button.confirm:hover {
  background-color: #c0392b;
}

.text-red-600 {
  margin-left: 10px;
  color: #d32f2f;
}

.select-wrapper {
  position: relative;
  display: block;
}

.select-wrapper::after {
  content: '';
  position: absolute;
  top: 50%;
  right: 15px;
  transform: translateY(-50%);
  
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid #555;
  
  pointer-events: none;
}

.select-wrapper:has(select:focus) {
  outline: none; 
  border-color: #42b983; 
  box-shadow: 0 0 0 3px rgba(66, 185, 131, 0.2);
  border-radius: 8px; 
}


@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
