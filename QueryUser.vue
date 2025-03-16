<template>
  <div class="query-container">
    <!-- 查询输入区域 -->
    <div class="input-section">
      <el-input
        v-model="phone"
        placeholder="请输入手机号"
        clearable
        style="width: 300px"
        @keyup.enter="handleSearch"
      />
      <el-button 
        type="primary" 
        :loading="loading"
        @click="handleSearch"
      >
        查询借阅记录
      </el-button>
    </div>

    <!-- 结果展示 -->
    <div v-if="resultVisible" class="result-card">
      <!-- 用户信息 -->
      <div class="user-info">
        <el-descriptions title="借阅人信息" :column="2" border>
          <el-descriptions-item label="姓名">{{ userInfo.name }}</el-descriptions-item>
          <el-descriptions-item label="学院">{{ userInfo.college }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ formatPhone(phone) }}</el-descriptions-item>
          <el-descriptions-item label="在借数量">
            <el-tag type="danger">{{ userInfo.books.length }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 书籍列表 -->
      <div class="book-list">
        <el-divider>在借书籍明细</el-divider>
        <el-table 
          :data="userInfo.books" 
          stripe 
          style="width: 100%"
          v-loading="loading"
        >
          <el-table-column prop="book_id" label="书籍ID" width="180"/>
          <el-table-column label="借阅日期" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.borrow_date) }}
            </template>
          </el-table-column>
          <el-table-column label="应还日期" width="180">
            <template #default="scope">
              <span :class="{ 'overdue': isOverdue(scope.row.due_date) }">
                {{ formatDate(scope.row.due_date) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="剩余天数" width="120">
            <template #default="scope">
              {{ remainingDays(scope.row.due_date) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button-group>
                <el-button 
                  type="primary" 
                  size="small"
                  @click="viewDetail(scope.row.book_id)"
                >
                  详情
                </el-button>
                <el-button 
                  type="danger" 
                  size="small"
                  :loading="scope.row.returning"
                  @click="handleReturn(scope.row)"
                >
                  归还
                </el-button>
              </el-button-group>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 错误提示 -->
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      style="margin-top: 20px"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// 响应式数据
const phone = ref('')
const userInfo = ref({
  name: '',
  college: '',
  books: []
})
const loading = ref(false)
const errorMessage = ref('')
const resultVisible = ref(false)

// 手机号验证
const validatePhone = () => {
  if (!phone.value.trim()) {
    errorMessage.value = '手机号不能为空'
    return false
  }
  if (!/^\d{11}$/.test(phone.value)) {
    errorMessage.value = '请输入有效的11位手机号'
    return false
  }
  return true
}

// 处理查询
const handleSearch = async () => {
  errorMessage.value = ''
  resultVisible.value = false
  
  if (!validatePhone()) return

  try {
    loading.value = true
    const { data } = await axios.post('http://localhost:8000/borrower_info', {
      borrower_phone: phone.value
    })

    if (data && data.name && data.books) {
      userInfo.value = {
        name: data.name,
        college: data.college,
        books: data.books.map(book => ({
          ...book,
          borrow_date: new Date(book.borrow_date),
          due_date: new Date(book.due_date),
          returning: false
        }))
      }
      resultVisible.value = true
    } else {
      throw new Error('返回数据格式异常')
    }
  } catch (err) {
    handleError(err)
  } finally {
    loading.value = false
  }
}

// 查看书籍详情
const viewDetail = (bookId) => {
  router.push({
    path: `/book/${bookId}`,
    query: { 
      phone: phone.value,
      from: 'borrow'
    }
  })
}

// 处理归还
const handleReturn = async (book) => {
  try {
    await ElMessageBox.confirm(
      `确认归还书籍 ${book.book_id} 吗？`,
      '归还确认',
      {
        confirmButtonText: '确认归还',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    book.returning = true
    
    await axios.post('http://localhost:8000/return_book', {
      book_id: book.book_id,
      borrower_phone: phone.value
    })

    // 更新本地数据
    userInfo.value.books = userInfo.value.books.filter(
      item => item.book_id !== book.book_id
    )
    
    ElMessage.success('归还成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`归还失败: ${error.response?.data?.detail || error.message}`)
    }
  } finally {
    book.returning = false
  }
}

// 错误处理
const handleError = (error) => {
  if (error.response) {
    switch (error.response.status) {
      case 500:
        errorMessage.value = '未找到该用户的借阅记录'
        break
      case 400:
        errorMessage.value = '请求参数格式错误'
        break
      default:
        errorMessage.value = `服务器错误 (${error.response.status})`
    }
  } else {
    errorMessage.value = error.message || '请求失败，请检查网络连接'
  }
}

// 工具函数
const formatDate = (date) => {
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const isOverdue = (dueDate) => {
  return dueDate < new Date()
}

const remainingDays = (dueDate) => {
  const diff = dueDate - new Date()
  return Math.max(Math.ceil(diff / (1000 * 60 * 60 * 24)), 0)
}

const formatPhone = (phone) => {
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
}
</script>

<style scoped>
.query-container {
  padding: 30px;
  max-width: 1000px;
  margin: 0 auto;
}

.input-section {
  display: flex;
  gap: 15px;
  margin-bottom: 30px;
  align-items: center;
}

.result-card {
  padding: 25px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  background: #fff;
}

.user-info {
  margin-bottom: 30px;
}

.book-list {
  margin-top: 25px;
}

.overdue {
  color: #ff4d4f;
  font-weight: 600;
}

:deep(.el-descriptions__title) {
  font-size: 16px;
  color: #606266;
}

.el-table {
  margin-top: 15px;
}

.el-button-group {
  display: flex;
  gap: 8px;
}

.el-button--danger {
  padding: 5px 10px;
}

.el-button--primary {
  padding: 5px 10px;
}
</style>