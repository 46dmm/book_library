from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import csv
from typing import Dict, List, Any, Optional
import os
import random
from ocr_processor import ocr_processor
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware  # 跨域中间件


# ================== 工具类 ==================
class IdGenerator:
    @staticmethod
    def new_hex_id(size: int = 8) -> str:
        """生成带时间戳的16进制ID（示例：5f3a8b2c）"""
        timestamp = int(datetime.now().timestamp())
        hex_ts = f"{timestamp:x}"[-4:]  # 取时间戳后4位十六进制
        return hex_ts + ''.join(random.choices("0123456789abcdef", k=size-4))

# ================== 数据访问层 ==================
class CSVRepository:
    def __init__(self, filename: str, schema: Dict[str, type], pk_field: str = "id"):
        self.filename = filename
        self.schema = schema
        self.pk_field = pk_field
        self.data: Dict[str, Dict] = {}
        
        # 自动创建CSV文件
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=schema.keys())
                writer.writeheader()

    def load(self):
        """加载CSV数据到内存"""
        with open(self.filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed = {
                    field: self._parse_value(field, row[field])
                    for field in self.schema
                }
                self.data[processed[self.pk_field]] = processed

    def _parse_value(self, field: str, value: str) -> Any:
        """类型转换处理器"""
        field_type = self.schema[field]
        
        if value == "":
            return None if field_type != str else ""
            
        if field_type == datetime:
            return datetime.fromisoformat(value)
        if field_type == bool:
            return value.lower() == "true"
        if issubclass(field_type, int):
            return int(value)
        return value

    def save(self, item: Dict) -> str:
        """保存单个记录"""
        if not item.get(self.pk_field):
            item[self.pk_field] = IdGenerator.new_hex_id()
            
        self.data[item[self.pk_field]] = item
        self._persist()
        return item[self.pk_field]

    def delete(self, item_id: str) -> bool:
        """删除记录"""
        if item_id in self.data:
            del self.data[item_id]
            self._persist()
            return True
        return False

    def find(self, **filters: Any) -> List[Dict]:

        """条件查询"""
        return [
        item 
        for item in self.data.values()
        if all(
            str(item.get(k, None)) == str(v)  # 统一转为字符串比较
            for k, v in filters.items()
        )
    ]
    def _persist(self):
        """持久化到CSV"""
        with open(self.filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.schema.keys())
            writer.writeheader()
            for item in self.data.values():
                writer.writerow({
                    field: self._serialize(field, value)
                    for field, value in item.items()
                })

    def _serialize(self, field: str, value: Any) -> str:
        """序列化处理"""
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

# ================== 业务逻辑层 ==================
class BookService:
    def __init__(self):
        self.book_repo = CSVRepository(
            filename="books.csv",
            schema={
                "id": str,
                "title": str,
                "author": str,
                "total": int,
                "available": int,
                "isbn": str,  # 新增字段
                "price": float  # 新增字段
            }
        )
        self.book_repo.load()
    def search_books(self, keyword: str, page: int, page_size: int) -> dict:
        """分页搜索书籍"""
        self.book_repo.load() 
        all_books = list(self.book_repo.data.values())
        filtered = [
            book for book in all_books
            if keyword.lower() in book["title"].lower() or 
               keyword.lower() in book["author"].lower()
        ]
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "data": filtered[start:end],
            "total": len(filtered),
            "page": page,
            "total_pages": (len(filtered) + page_size - 1) // page_size
        }
    
    def delete_book(self, book_id: str) -> bool:
        """删除书籍"""
        return self.book_repo.delete(book_id)
      
    def create_book(self, book_data: Dict) -> str:
        """创建新书（增加ISBN校验）"""
        if "isbn" in book_data and not self._validate_isbn(book_data["isbn"]):
            raise ValueError("无效的ISBN号码")
            
        return self.book_repo.save({
            **book_data,
            "available": book_data.get("total", 1)
            })
           

    @staticmethod
    def _validate_isbn(isbn: str) -> bool:
        """ISBN-13校验算法"""
        if len(isbn) != 13 or not isbn.isdigit():
            return False
        total = sum(int(ch) * (3 if i%2 else 1) for i, ch in enumerate(isbn[:12]))
        check = (10 - total % 10) % 10
        return check == int(isbn[-1])
    def get_book(self, book_id: str) -> Optional[dict]:
        """获取图书详情"""
        return self.book_repo.data.get(book_id)


    

class BorrowService:
    def __init__(self):
        self.borrow_repo = CSVRepository(
            filename="borrows.csv",
            schema={
                "id": str,
                "book_id": str,
                "borrower_phone": str,
                "borrower_name": str,
                "borrower_college": str,
                "borrow_date": datetime,
                "due_date": datetime,
                "returned": bool
            }
        )
        self.book_service = BookService()
        self.book_service.book_repo.load() 

    def get_borrower_info(self, phone: str) -> dict:
        """获取借阅人详细信息"""
        records = self.borrow_repo.find(
            borrower_phone=phone,
            returned=False
        )
        
        if not records:
            return None
            
        # 从第一条记录中提取用户信息（假设用户信息一致）
        sample_record = records[0]
        return {
            "name": sample_record["borrower_name"],
            "college": sample_record["borrower_college"],
            "total_borrowed": len(records),
            "books": [
                {
                    "book_id": r["book_id"],
                    "borrow_date": r["borrow_date"].isoformat(),
                    "due_date": r["due_date"].isoformat()
                }
                for r in records
            ]
        }
    
    def create_borrow_record(self, borrow_data: Dict) -> str:
        """创建借阅记录"""
        if not borrow_data.get("id"):
            borrow_data["id"] = IdGenerator.new_hex_id()
        return self.borrow_repo.save(borrow_data)

    def return_book(self, book_id: str, borrower_phone: str) -> dict:
        """归还图书"""
        # 查找未归还记录
        records = self.borrow_repo.find(
            book_id=book_id,
            borrower_phone=borrower_phone,
            returned=False
        )
        
        if not records:
            raise ValueError("未找到借阅记录")
        
        # 更新借阅记录
        record = records[0]
        record["returned"] = True
        self.borrow_repo.save(record)
        
        # 恢复库存
        book = self.book_service.get_book(book_id)
        if book:
            book["available"] += 1
            self.book_service.book_repo.save(book)
            
        return {"message": "归还成功"}
    
    def get_borrow_history(self, borrower_phone: str) -> list:
        """获取用户借阅历史"""
        return self.borrow_repo.find(borrower_phone=borrower_phone)
    
    def calculate_book_stats(self, book_id: str) -> dict:
        """计算书籍统计信息"""
        book = self.book_service.get_book(book_id)
        if not book:
            raise ValueError("书籍不存在")
        
        borrowed = book["total"] - book["available"]
        borrow_records = self.borrow_repo.find(book_id=book_id)
        
        # 计算平均借阅天数
        total_days = 0
        count = 0
        for record in borrow_records:
            if record["returned"]:
                days = (record["due_date"] - record["borrow_date"]).days
                total_days += days
                count += 1
                
        avg_days = total_days / count if count > 0 else 0
        
        # 计算最早归还天数
        now = datetime.now()
        earliest_due = min(
            (record["due_date"] for record in borrow_records if not record["returned"]),
            default=None
        )
        
        earliest_days = (earliest_due - now).days if earliest_due else 0
        earliest_days = max(earliest_days, 0)
        
        return {
            "available": book["available"],
            "borrowed": borrowed,
            "average_borrow_days": avg_days,
            "earliest_due_days": earliest_days
        }
    
    def borrow_book(self, borrow_data: Dict) -> Dict:
        """借阅操作"""

        self.book_service.book_repo.load() 
        book = self.book_service.get_book(borrow_data["book_id"])
        if not book or book["available"] <= 0:
            raise ValueError("图书不可借阅")
        existing = any(
            record for record in self.borrow_repo.find(
                book_id=borrow_data["book_id"],
                borrower_phone=borrow_data["borrower_phone"],
                returned=False
            )
        )
        if existing:
            raise ValueError("同一手机号不可重复借阅")

        # 更新图书库存
        book["available"] -= 1
        self.book_service.book_repo.save(book)
        self.book_service.book_repo._persist() 


        # 创建借阅记录
        new_record = {
        "book_id": borrow_data["book_id"],
        "borrower_phone": borrow_data["borrower_phone"],
        "borrower_name": borrow_data["borrower_name"],
        "borrower_college": borrow_data["borrower_college"],
        "borrow_date": datetime.now(),
        "due_date": datetime.now() + timedelta(days=14),
        "returned": False
    }
        self.borrow_repo.save(new_record)
        self.borrow_repo._persist()
        return {"message": "借阅成功"}

# ================== API层 ==================

book_service = BookService()
borrow_service = BorrowService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化加载数据
    book_service.book_repo.load()
    borrow_service.borrow_repo.load()
    yield
    # 退出时自动保存
    book_service.book_repo._persist()
    borrow_service.borrow_repo._persist()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许所有来源，生产环境应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法 (GET/POST等)
    allow_headers=["*"],   # 允许所有请求头
)
# 全局 OPTIONS 处理器
@app.options("/{path:path}")
async def options_handler():
    return {"message": "CORS preflight accepted"}

# 数据模型
class BookCreate(BaseModel):
    title: str
    author: str
    total: int
    isbn: Optional[str] = None  # 新增字段
    price: Optional[float] = None  # 新增字段

class ScanRequest(BaseModel):
    scan_type: str  # cover/info/price
    temp_id: Optional[str] = None

class ScanResponse(BaseModel):
    temp_id: str
    metadata: dict
    next_step: Optional[str] = None

class BorrowRequest(BaseModel):
    book_id: str
    borrower_phone: str
    borrower_name: str
    borrower_college: str
class SearchRequest(BaseModel):
    keyword: str
    page: int = 1
    page_size: int = 10

class BookDetailRequest(BaseModel):
    book_id: str

class BorrowerLoansRequest(BaseModel):
    borrower_phone: str

class ReturnRequest(BaseModel):
    book_id: str
    borrower_phone: str

class BookResponse(BookCreate):
    id: str
    available: int

# API端点
@app.post("/create_books")
async def create_book(book: BookCreate):
    try:
        book_id = book_service.create_book(book.dict())
        return {"id": book_id}
    except Exception as e:
        raise HTTPException(400, str(e))
    
@app.post("/borrower_info")
async def get_borrower_info(request: BorrowerLoansRequest):
    try:
        info = borrow_service.get_borrower_info(request.borrower_phone)
        if not info:
            raise HTTPException(status_code=404, detail="用户不存在或无借阅记录")
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/borrow")
async def borrow_book(request: BorrowRequest):
    try:
        return borrow_service.borrow_book(request.dict())
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/search_books")
async def search_books(request: SearchRequest):
    try:
        result = book_service.search_books(
            keyword=request.keyword,
            page=request.page,
            page_size=request.page_size
        )
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/book_detail")
async def book_detail(request: BookDetailRequest):
    try:
        stats = borrow_service.calculate_book_stats(request.book_id)
        return stats
    except ValueError as e:
        raise HTTPException(404, str(e))

@app.post("/borrower_loans")
async def borrower_loans(request: BorrowerLoansRequest):
    try:
        records = borrow_service.borrow_repo.find(
            borrower_phone=request.borrower_phone,
            returned=False
        )
        return {"borrowed_count": len(records)}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/return_book")
async def return_book(request: ReturnRequest):
    try:
        return borrow_service.return_book(
            book_id=request.book_id,
            borrower_phone=request.borrower_phone
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

class SystemStats(BaseModel):
    books_sorts: int
    available_books: int
    borrowed_books: int

@app.post("/stats", response_model=SystemStats)
async def get_system_stats():
    books = book_service.book_repo.data.values()
    return {
        "books_sorts": len(books),
        "available_books": sum(b["available"] for b in books),
        "borrowed_books": sum(b["total"] - b["available"] for b in books)
    }

@app.post("/del_books/{book_id}")
async def delete_book(book_id: str):
    if book_service.delete_book(book_id):
        return {"message": "Book deleted"}
    raise HTTPException(404, "Book not found")

temp_scan_data: Dict[str, Dict] = {}
@app.post("/scan_book")
async def scan_book_page(
    file: UploadFile = File(..., description="图书照片"),
    scan_type: str = Form("cover"),
    temp_id: Optional[str] = Form(None)
):
    try:
        # 验证文件类型
        if file.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(400, "仅支持JPEG/PNG格式")
        
        # 处理临时数据存储
        current_data = {}
        if temp_id:
            current_data = temp_scan_data.get(temp_id, {})
        else:
            temp_id = IdGenerator.new_hex_id()
        
        # 处理图像
        image_bytes = await file.read()
        
        # 分步骤处理不同扫描类型
        if scan_type == "cover":
            # 封面识别只处理标题
            title = ocr_processor.extract_cover_info(image_bytes)
            current_data.update({
                "title": title
            })
        elif scan_type == "info":
            # 详情页识别作者和ISBN
            info = ocr_processor.extract_printing_info(image_bytes)
            current_data.update(info)
        elif scan_type == "price":
            # 价格页识别价格
            price = ocr_processor.extract_price(image_bytes)
            current_data["price"] = price
        else:
            raise HTTPException(400, "无效的扫描类型")
        
        # 更新临时存储
        temp_scan_data[temp_id] = current_data
        
        # 确定下一步操作
        next_step_map = {
            "cover": "info",
            "info": "price",
            "price": None
        }
        
        return {
            "temp_id": temp_id,
            "metadata": current_data,
            "next_step": next_step_map.get(scan_type)
        }
        
    except ValueError as ve:
        raise HTTPException(400, f"识别失败: {str(ve)}")
    except Exception as e:
        raise HTTPException(500, f"处理失败: {str(e)}")
# 修改最终提交接口
@app.post("/finalize_book")
async def create_book_from_scan(metadata: dict):
    try:
        # 验证必要字段
        required_fields = ["title", "author", "isbn"]
        if any(f not in metadata for f in required_fields):
            missing = [f for f in required_fields if f not in metadata]
            raise HTTPException(400, f"缺少必要字段: {missing}")
        
        # 创建正式记录
        book_data = {
            "title": metadata["title"],
            "author": metadata["author"],
            "total": metadata.get("total", 1),
            "isbn": metadata["isbn"],
            "price": metadata.get("price", 0.0)
        }
        
        # 验证ISBN格式
        if not BookService._validate_isbn(book_data["isbn"]):
            raise HTTPException(400, "无效的ISBN号码")
        
        book_id = book_service.create_book(book_data)
        return {"id": book_id}
    except ValueError as e:
        raise HTTPException(400, str(e))