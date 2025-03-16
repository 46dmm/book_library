from paddleocr import PaddleOCR
import re
import cv2
import numpy as np
from typing import Tuple, List
from datetime import datetime  # 新增导入



class PaddleProcessor:
    def __init__(self):
        # 初始化中英文OCR模型（自动下载预训练模型）
        self.ocr = PaddleOCR(
            use_angle_cls=True,  # 启用方向分类
            lang="ch",           # 中英文混合
            show_log=False,      # 关闭日志输出
            use_gpu=False        # 根据环境启用GPU
             
        )
        self.debug_file = "ocr_result.txt"
    
    def extract_printing_info(self, image_bytes: bytes) -> dict:
        """印刷页信息结构化提取"""
        img = self._preprocess(image_bytes)
        blocks = self._find_text_blocks(img)
        full_text = "\n".join([b[1][0] for b in blocks])
        
        # 保存调试信息到统一文件
        debug_filename = "printing_debug.txt"
        with open(debug_filename, "a", encoding="utf-8") as f:
            f.write(f"\n\n{'='*40}\n")
            f.write(f"识别时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"有效文本块数：{len(blocks)}\n")
            f.write(f"{'-'*40}\n")
            
            # 写入原始识别结果
            for idx, block in enumerate(blocks, 1):
                text = block[1][0]
                conf = block[1][1]
                f.write(f"[块{idx}] 置信度{conf:.2f}: {text}\n")
                
            f.write(f"{'-'*40}\n")
            f.write(f"合并文本：\n{full_text}\n")
            f.write(f"{'='*40}\n")
        
        print(f"调试信息已追加至：{debug_filename}")
        
        # 原有处理逻辑保持不变...
        result = {'author': None, 'isbn': None}
        # ... [原有作者和ISBN识别代码]
        
        return result
    def _find_text_blocks(self, img: np.ndarray) -> List[Tuple]:
        """增强OCR稳定性并保存结果"""
        try:
            result = self.ocr.ocr(img, cls=True)
            with open(self.debug_file, "a", encoding="utf-8") as f:
                f.write(f"\n\n===== 新的OCR识别结果 =====\n")
                f.write(f"输入图像尺寸: {img.shape}\n")
                if result:
                    for line in result:
                        if line:
                            points = line[0]
                            text = line[1][0]
                            confidence = line[1][1]
                            f.write(f"坐标: {points} 文本: {text} 置信度: {confidence:.2f}\n")
                else:
                    f.write("未识别到任何文本\n")
            
            # 数据校验和转换
            valid_blocks = []
            for res in result if result else []:
                if res and len(res) >= 2:
                    try:
                        # 转换坐标点为整数
                        points = np.array(res[0], dtype=np.int32).reshape(-1, 2)
                        if points.shape[0] >= 4:  # 至少需要4个点组成四边形
                            valid_blocks.append((points, (res[1][0], res[1][1])))
                    except Exception as e:
                        print(f"坐标转换异常: {str(e)}")
            return valid_blocks
        except Exception as e:
            print(f"OCR处理异常: {str(e)}")
            return []

    def _preprocess(self, image_bytes: bytes) -> np.ndarray:
        """通用图像预处理"""
        img_array = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        # 自适应直方图均衡化
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        lab[...,0] = clahe.apply(lab[...,0])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        return img

    def _find_text_blocks(self, img: np.ndarray) -> List[Tuple]:
        """使用PaddleOCR检测文本区域"""
        result = self.ocr.ocr(img, cls=True)
        return [line for res in result for line in res] if result else []

    def extract_cover_info(self, image_bytes: bytes) -> str:
        """封面识别优化逻辑（根据最大字号识别）"""
        img = self._preprocess(image_bytes)
        blocks = self._find_text_blocks(img)
        
        max_text = None
        max_height = 0
        
        for block in blocks:
            text = block[1][0]
            confidence = block[1][1]
            
            # 获取文本框坐标并计算高度
            points = np.array(block[0], dtype=np.int32)
            _, _, _, h = cv2.boundingRect(points)
            
            # 根据高度和置信度综合判断（置信度>0.6）
            if h > max_height and confidence > 0.6:
                max_height = h
                max_text = text
        
        # 备选方案：无置信度过滤
        if not max_text and blocks:
            max_block = max(blocks, key=lambda b: cv2.boundingRect(np.array(b[0]))[3])
            max_text = max_block[1][0]
        
        if max_text:
            # 清洗结果（移除特殊符号）
            clean_text = re.sub(r'[《》【】\*]', '', max_text).strip()
            return clean_text[:50]  # 防止过长异常文本
        
        raise ValueError("无法识别书名")

    def extract_printing_info(self, image_bytes: bytes) -> dict:
        """印刷页信息结构化提取"""
        img = self._preprocess(image_bytes)
        blocks = self._find_text_blocks(img)
        full_text = "\n".join([b[1][0] for b in blocks])
        
        result = {'author': None, 'isbn': None}
        
        # 修改后的作者识别模式
        author_patterns = [
            # 新增机构识别模式（匹配示例：XXX编）
            r'^([\u4e00-\u9fa5]+?(大学|学院|系|研究所|教研室))编?$',
            # 原有着作责任模式
            r'([\u4e00-\u9fa5]{2,4})(主编|编著|著)',
            r'(?:主编|编著)[:：]\s*([^\n]+)',
            r'([\u4e00-\u9fa5]{2,4})\s+(主编|编著)',
            r'作者[:：]\s*([^\n]+)',
            r'著\s*([^\n]+)'
        ]
        
        for pattern in author_patterns:
            if match := re.search(pattern, full_text):
                author = match.group(1) if '主编' in pattern else match.group(2)
                result['author'] = author.strip('：:')
                break
    
        
        # ISBN识别（带校验）
        isbn_candidates = re.findall(r'\b(?:ISBN|标准书号)[-:\s]*(97[89][-\d]{10,})\b', full_text)
        for candidate in isbn_candidates:
            clean_isbn = candidate.replace('-', '').replace(' ', '')
            if self.validate_isbn(clean_isbn):
                result['isbn'] = clean_isbn
                break
        
        if not result['isbn']:
            raise ValueError("ISBN校验失败")
        
        return result

    def extract_price(self, image_bytes: bytes) -> float:
        """价格识别"""
        try:
            img = self._preprocess(image_bytes)
            if img.size == 0:
                raise ValueError("图像预处理失败")

            # 直接处理完整图片
            blocks = []
            raw_blocks = self._find_text_blocks(img)
            for block in raw_blocks:
                # 增强坐标校验
                points = np.array(block[0], dtype=np.int32)
                if points.size < 8:  # 至少4个点(x,y)
                    continue
                if not np.isfinite(points).all():
                    continue
                blocks.append((points, block[1]))

            # 有效性检查
            valid_blocks = []
            for b in blocks:
                try:
                    # 安全获取包围盒
                    x, y, w, h = cv2.boundingRect(b[0])
                    if w > 0 and h > 0:
                        valid_blocks.append(b)
                except:
                    continue

            if not valid_blocks:
                raise ValueError("未识别到有效文本")

            # 合并文本逻辑
            sorted_blocks = sorted(valid_blocks, 
                                key=lambda b: (cv2.boundingRect(b[0])[1], 
                                            cv2.boundingRect(b[0])[0]))
            
            merged_text = " ".join([b[1][0] for b in sorted_blocks])
            print(f"合并文本: {merged_text}")  # 调试日志

            # 增强价格匹配模式
            patterns = [
                r'(?:(?:定价|价格|￥|¥)\s*[:：]?)\s*(\d+\.?\d*)',
                r'\b\d+\.\d{2}\b',
                r'(?<!\d)(\d+)\s*元整?',
                r'(?:USD|CNY|EUR)\s*(\d+\.\d{2})'
            ]

            for pattern in patterns:
                if match := re.search(pattern, merged_text):
                    try:
                        price_str = match.group(1).replace(',', '')
                        price = round(float(price_str), 2)
                        if 0 < price < 10000:
                            return price
                    except (ValueError, TypeError):
                        continue

            raise ValueError("未找到有效价格信息")

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"价格识别失败: {str(e)}")
    def _find_text_blocks(self, img: np.ndarray) -> List[Tuple]:
        """增强OCR稳定性"""
        try:
            result = self.ocr.ocr(img, cls=True)
            # 结构校验
            if not isinstance(result, list):
                return []
            return [line for res in result if res is not None for line in res]
        except Exception as e:
            print(f"OCR处理异常: {str(e)}")
            return []
    @staticmethod
    def validate_isbn(isbn: str) -> bool:
        """ISBN-13校验"""
        if len(isbn) != 13 or not isbn.isdigit():
            return False
        total = sum(int(digit) * (3 if i%2 else 1) for i, digit in enumerate(isbn[:12]))
        check = (10 - total % 10) % 10
        return check == int(isbn[-1])

# 单例实例化（推荐）
ocr_processor = PaddleProcessor()