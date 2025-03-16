import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000', // FastAPI服务地址
  timeout: 5000
})

export default {
  // 借阅人查询
  getUserInfo(phone) {
    return api.post('/borrower_loans', { phone })
  },
  
  // 图书搜索
  searchBooks(params) {
    return api.post('/search_books', params)
  },
  
  // 借阅登记
  borrowBook(data) {
    return api.post('/borrow', data)
  }
}