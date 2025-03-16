<template>
  <div class="borrow-container">
    
    <div class="form-wrapper">
      <h2>图书借阅</h2>
      <el-form :model="form" label-width="120px" :rules="rules" ref="borrowForm">
        <!-- 图书搜索部分 -->
        <el-form-item label="图书搜索" prop="keyword">
          <el-input 
            v-model="form.keyword" 
            placeholder="输入书名/作者"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button @click="handleSearch" :loading="loadingSearch">搜索</el-button>
            </template>
          </el-input>
        </el-form-item>
        
        
        <!-- 搜索结果列表 -->
        <el-table 
          :data="searchResults" 
          highlight-current-row 
          @row-click="selectBook"
          v-loading="loadingSearch"
          style="width: 100%"
        >
          <el-table-column prop="title" label="书名" width="200"/>
          <el-table-column prop="author" label="作者" width="180"/>
          <el-table-column prop="available" label="可借数量" width="120">
            <!-- 原有标签逻辑 -->
          </el-table-column>
          
          <!-- 操作列 -->
          <el-table-column 
            label="操作" 
            width="120" 
            fixed="right"
          >
            <template #default="scope">
              <el-button 
                size="small" 
                type="primary"
                style="min-width: 60px"
                @click.stop="viewDetail(scope.row)"
                :disabled="scope.row.available <= 0"
              >
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        

        

        <!-- 分页控件 -->
        <el-pagination
          v-model:current-page="pagination.current"
          :page-size="pagination.size"
          :total="pagination.total"
          layout="prev, pager, next"
          @current-change="handlePageChange"
          style="margin-top: 15px"
        />

        <!-- 借阅人信息 -->
        <el-divider />
        <h3>借阅人信息</h3>
        <el-form-item label="手机号" prop="phone" required>
          <el-input v-model="form.phone" placeholder="11位手机号"/>
        </el-form-item>
        <el-form-item label="姓名" prop="name" required>
          <el-input v-model="form.name"/>
        </el-form-item>
        <el-form-item label="学院" prop="college" required>
          <el-input v-model="form.college"/>
        </el-form-item>

        <el-form-item>
          <el-button 
            type="primary" 
            @click="submitBorrow"
            :loading="loadingSubmit"
          >
            确认借阅
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const form = reactive({
  keyword: '',
  phone: '',
  name: '',
  college: '',
  selectedBook: null
})

const pagination = reactive({
  current: 1,
  size: 10,
  total: 0
})

const searchResults = ref([])
const loadingSearch = ref(false)
const loadingSubmit = ref(false)

// 表单验证规则
const rules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^\d{11}$/, message: '手机号必须是11位数字', trigger: 'blur' }
  ],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  college: [{ required: true, message: '请输入学院', trigger: 'blur' }]
}

// 搜索处理
const handleSearch = () => {
  pagination.current = 1
  searchBooks()
}

// 分页处理
const handlePageChange = (newPage) => {
  pagination.current = newPage
  searchBooks()
}

const searchBooks = async () => {
  try {
    loadingSearch.value = true
    const response = await axios.post('http://localhost:8000/search_books', {
      keyword: form.keyword,
      page: pagination.current,
      page_size: pagination.size
    })
    
    searchResults.value = response.data?.data || []
    pagination.total = response.data?.total || 0
    
  } catch (error) {
    ElMessage.error('搜索失败: ' + error.message)
  } finally {
    loadingSearch.value = false
  }
}

const selectBook = (book) => {
  if (book.available <= 0) {
    ElMessage.warning('该图书暂无库存')
    return
  }
  form.selectedBook = book
  ElMessage.success(`已选择: ${book.title}`)
}

const submitBorrow = async () => {
  try {
    if (!form.selectedBook) {
      ElMessage.warning('请先选择要借阅的图书')
      return
    }
    
    loadingSubmit.value = true
    await axios.post('http://localhost:8000/borrow', {
      book_id: form.selectedBook.id,
      borrower_phone: form.phone,
      borrower_name: form.name,
      borrower_college: form.college
    })
    
    // 本地更新库存数量（实时反馈）
    const index = searchResults.value.findIndex(b => b.id === form.selectedBook.id)
    if (index > -1) {
      searchResults.value[index].available -= 1
    }
    
    // 重置表单
    form.phone = ''
    form.name = ''
    form.college = ''
    form.selectedBook = null
    
    ElMessage.success('借阅成功')
  } catch (error) {
    ElMessage.error(`借阅失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    loadingSubmit.value = false
  }
}
import { useRouter } from 'vue-router'

const router = useRouter()

const viewDetail = (book) => {
  router.push({
    path: `/book/${book.id}`,
    query: { 
      title: book.title,
      author: book.author 
    }
  })
}
</script>

<style scoped>
.borrow-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}
.form-wrapper {
  margin-top: 20px;
  padding: 20px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fff;
}
</style>