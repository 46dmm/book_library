<template>
  <div class="scan-process">
    <h2>拍照录入图书</h2>
    
    <!-- 步骤指示 -->
    <div class="steps">
      <div 
        :class="{active: currentStep === 'cover'}" 
        @click="selectStep('cover')"
      >
        1. 拍摄封面
      </div>
      <div 
        :class="{active: currentStep === 'info'}" 
        @click="selectStep('info')"
      >
        2. 拍摄信息页
      </div>
      <div 
        :class="{active: currentStep === 'price'}" 
        @click="selectStep('price')"
      >
        3. 拍摄价格页
      </div>
    </div>

    <!-- 拍照区域 -->
    <input 
      type="file" 
      accept="image/*" 
      capture="environment"
      @change="handleUpload"
    >

    <!-- 可编辑的预览信息 -->
    <div v-if="currentBook" class="preview">
      <h3>识别结果</h3>
      
      <div class="form-item">
        <label>书名：</label>
        <input v-model="currentBook.title" class="edit-input">
      </div>

      <div class="form-item">
        <label>作者：</label>
        <input v-model="currentBook.author" class="edit-input">
      </div>

      <div class="form-item">
        <label>ISBN：</label>
        <input v-model="currentBook.isbn" class="edit-input">
      </div>

      <div class="form-item">
        <label>价格：</label>
        <input 
          v-model="currentBook.price" 
          type="number" 
          class="edit-input"
          min="0"
          step="0.01"
        >
      </div>
      
      <button 
        v-if="showConfirm"
        @click="submitBook"
        class="submit-btn"
      >
        ✅ 确认录入
      </button>
    </div>

    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const currentStep = ref('cover')
const tempId = ref(null)
const currentBook = ref(null)
const showConfirm = ref(false)
const errorMessage = ref('')
const manualStepSelected = ref(false)

// 以下handleUpload、selectStep、submitBook等方法保持原样不变
const handleUpload = async (e) => {
  errorMessage.value = ''
  const file = e.target.files[0]
  const formData = new FormData()
  formData.append('file', file)
  formData.append('scan_type', currentStep.value)
  if (tempId.value) formData.append('temp_id', tempId.value)

  try {
    const { data } = await axios.post('http://localhost:8000/scan_book', formData, {
      headers: {'Content-Type': 'multipart/form-data'}
    })
    
    tempId.value = data.temp_id
    currentBook.value = data.metadata
    
    if (data.next_step === 'info') {
      currentStep.value = 'info'
    } else if (data.next_step === 'price') {
      currentStep.value = 'price'
    } else {
      showConfirm.value = true
    }
  } catch (err) {
    errorMessage.value = `识别失败: ${err.response?.data?.detail || err.message}`
    manualStepSelected.value = false
    if (currentStep.value === 'cover') {
      currentStep.value = 'info'
    } else if (currentStep.value === 'info') {
      currentStep.value = 'price'
    } else if (currentStep.value === 'price') {
      showConfirm.value = true
    }
  }
}

const selectStep = (step) => {
  currentStep.value = step
  manualStepSelected.value = true
}

const submitBook = async () => {
  try {
    const { data } = await axios.post('http://localhost:8000/finalize_book', currentBook.value)
    alert(`图书录入成功！ID: ${data.id}`)
    resetProcess()
  } catch (err) {
    errorMessage.value = `录入失败: ${err.response?.data?.detail || err.message}`
  }
}

const resetProcess = () => {
  currentStep.value = 'cover'
  tempId.value = null
  currentBook.value = null
  showConfirm.value = false
  errorMessage.value = ''
  manualStepSelected.value = false
}
</script>

<style scoped>
.steps {
  display: flex;
  gap: 2rem;
  margin: 1rem 0;
}
.steps div {
  padding: 0.5rem;
  border: 1px solid #ccc;
  cursor: pointer;
  transition: all 0.3s;
}
.steps .active {
  background: #409eff;
  color: white;
}

.preview {
  margin-top: 2rem;
  padding: 2rem;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,.1);
}

.form-item {
  margin: 1.2rem 0;
  display: flex;
  align-items: center;
}

.form-item label {
  width: 80px;
  text-align: right;
  margin-right: 1rem;
}

.edit-input {
  flex: 1;
  border: 1px solid #dcdfe6;
  padding: 8px 15px;
  border-radius: 4px;
  transition: border-color 0.3s;
}

.edit-input:focus {
  border-color: #409eff;
  outline: none;
}

.submit-btn {
  display: block;
  width: 100%;
  background: #67c23a;
  color: white;
  padding: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 1.5rem;
  transition: background 0.3s;
}

.submit-btn:hover {
  background: #5daf34;
}

.error-message {
  color: #f56c6c;
  margin-top: 1rem;
  padding: 10px;
  background: #fef0f0;
  border-radius: 4px;
}
</style>