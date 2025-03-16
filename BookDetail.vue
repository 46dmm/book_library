<template>
  <div class="detail-container">
    <el-button type="primary" @click="$router.go(-1)" plain>返回上一页</el-button>
    
    <div class="detail-card" v-loading="loading">
      <h2>{{ bookInfo.title }}</h2>
      <el-divider />
      
      <el-descriptions :column="2" border>
        <el-descriptions-item label="在架数量">
          <el-tag type="success">{{ bookInfo.available }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="已借数量">
          <el-tag type="danger">{{ bookInfo.borrowed }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="平均借阅天数">
          {{ bookInfo.average_borrow_days || 0 }} 天
        </el-descriptions-item>
        <el-descriptions-item label="最早归还">
          {{ earliestReturnDays }} 天后
        </el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const route = useRoute()
const bookId = route.params.id

const bookInfo = ref({
  title: '',
  available: 0,
  borrowed: 0,
  average_borrow_days: 0
})

const earliestReturnDays = ref(0)
const loading = ref(false)

const loadData = async () => {
  try {
    loading.value = true
    const { data } = await axios.post('http://localhost:8000/book_detail', {
      book_id: bookId
    })
    
    bookInfo.value = {
      title: data.title,
      available: data.available,
      borrowed: data.borrowed,
      average_borrow_days: data.average_borrow_days
    }
    earliestReturnDays.value = data.earliest_due_days > 0 
      ? data.earliest_due_days 
      : '无未归还记录'
      
  } catch (error) {
    ElMessage.error('数据加载失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>