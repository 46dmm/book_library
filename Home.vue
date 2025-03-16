<template>
  <div class="main-menu">
    <el-card shadow="hover" @click="$router.push('/QueryUser')">
      <h3>借阅人查询</h3>
    </el-card>
    <el-card shadow="hover" @click="$router.push('/BookReturn')">
      <h3>图书归还</h3>
    </el-card>
    <el-card shadow="hover" @click="$router.push('/BorrowBook')">
      <h3>图书借阅</h3>
    </el-card>
    <el-card shadow="hover" @click="$router.push('/create_book')">
      <h3>拍照录入图书</h3>
    </el-card>
  </div>
</template>

<style>
.main-menu {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  padding: 20px;
}
</style>