<template>
  <div class="return-container">
    
    <div class="form-wrapper">
      <h2>快速归还</h2>
      <el-form 
        :model="form" 
        label-width="100px"
        :rules="rules"
        ref="returnForm"
      >
        <!-- 手机号输入 -->
        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="form.phone"
            placeholder="请输入借阅时登记的手机号"
            clearable
          />
        </el-form-item>

        <!-- 书籍ID输入 -->
        <el-form-item label="书籍ID" prop="bookId">
          <el-input
            v-model="form.bookId"
            placeholder="可在图书扉页找到的ID"
            clearable
          />
        </el-form-item>

        <!-- 操作按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            @click="handleReturn"
            :loading="loading"
          >
            立即归还
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 结果提示 -->
      <el-alert 
        v-if="resultMessage"
        :title="resultMessage"
        :type="resultType"
        show-icon
        class="result-alert"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const form = reactive({
  phone: '',
  bookId: ''
})

const rules = reactive({
  phone: [
    { required: true, message: '手机号不能为空', trigger: 'blur' },
    { pattern: /^\d{11}$/, message: '请输入11位手机号', trigger: 'blur' }
  ],
  bookId: [
    { required: true, message: '书籍ID不能为空', trigger: 'blur' },
    { pattern: /^[a-f0-9]{8}$/, message: 'ID为8位十六进制数', trigger: 'blur' }
  ]
})

const loading = ref(false)
const resultMessage = ref('')
const resultType = ref('info')

const handleReturn = async () => {
  try {
    loading.value = true
    resultMessage.value = ''
    
    const response = await axios.post('http://localhost:8000/return_book', {
      book_id: form.bookId,
      borrower_phone: form.phone
    })

    resultType.value = 'success'
    resultMessage.value = `书籍 ${form.bookId} 归还成功`
    
    // 清空表单
    form.phone = ''
    form.bookId = ''
    
  } catch (error) {
    resultType.value = 'error'
    resultMessage.value = `归还失败: ${error.response?.data?.detail || error.message}`
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.return-container {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.form-wrapper {
  margin-top: 20px;
  padding: 25px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.result-alert {
  margin-top: 20px;
}

.el-form-item {
  margin-bottom: 22px;
}
</style>