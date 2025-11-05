from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os
from pathlib import Path


# 创建 FastAPI 应用实例
app = FastAPI(
    title="TA Agent API",
    description="Technical Analysis Agent Backend API",
    version="0.1.0"
)

# 反馈文件目录
FEEDBACK_DIR = Path(__file__).parent / "feedback_output"

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 定义数据模型
class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    quantity: int = 0


class Message(BaseModel):
    message: str


# 根路由
@app.get("/")
async def root():
    """根路由 - 返回 API 欢迎信息"""
    return {
        "message": "Welcome to TA Agent API",
        "version": "0.1.0",
        "docs": "/docs"
    }


# 健康检查路由
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


# GET 示例 - 带路径参数
@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Optional[str] = None):
    """
    获取指定 ID 的项目
    - item_id: 项目 ID
    - q: 可选的查询参数
    """
    if item_id < 1:
        raise HTTPException(status_code=400, detail="Item ID must be positive")
    
    result = {"item_id": item_id, "name": f"Item {item_id}"}
    if q:
        result["query"] = q
    return result


# POST 示例 - 创建资源
@app.post("/items/", response_model=Item)
async def create_item(item: Item):
    """
    创建新项目
    """
    return item


# PUT 示例 - 更新资源
@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    """
    更新指定 ID 的项目
    """
    return {"item_id": item_id, **item.dict()}


# DELETE 示例
@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    """
    删除指定 ID 的项目
    """
    return {"message": f"Item {item_id} deleted successfully"}


# 获取学生反馈报告列表
@app.get("/api/feedback/{student_id}")
async def get_student_feedback(student_id: str):
    """
    获取指定学号的所有反馈报告
    """
    if not FEEDBACK_DIR.exists():
        raise HTTPException(status_code=500, detail="Feedback directory not found")
    
    # 查找该学号的所有反馈文件
    feedback_files = list(FEEDBACK_DIR.glob(f"{student_id}_*.md"))
    
    if not feedback_files:
        raise HTTPException(status_code=404, detail=f"No feedback found for student {student_id}")
    
    # 返回文件列表
    results = []
    for file_path in feedback_files:
        # 从文件名提取作业信息 (例如: 12210211_pa6p1_feedback.md)
        filename = file_path.stem  # 去掉 .md 后缀
        parts = filename.split('_')
        if len(parts) >= 2:
            assignment = parts[1]  # pa6p1
        else:
            assignment = "unknown"
        
        results.append({
            "filename": file_path.name,
            "assignment": assignment,
            "path": str(file_path)
        })
    
    return {
        "student_id": student_id,
        "count": len(results),
        "feedbacks": sorted(results, key=lambda x: x["assignment"])
    }


# 获取具体的反馈报告内容
@app.get("/api/feedback/{student_id}/{assignment}")
async def get_feedback_content(student_id: str, assignment: str):
    """
    获取指定学号和作业的反馈报告内容
    """
    if not FEEDBACK_DIR.exists():
        raise HTTPException(status_code=500, detail="Feedback directory not found")
    
    # 构建文件路径
    filename = f"{student_id}_{assignment}_feedback.md"
    file_path = FEEDBACK_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Feedback file not found: {filename}")
    
    # 读取文件内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "student_id": student_id,
            "assignment": assignment,
            "filename": filename,
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


# 获取所有学生列表
@app.get("/api/students")
async def get_all_students():
    """
    获取所有有反馈报告的学生列表
    """
    if not FEEDBACK_DIR.exists():
        raise HTTPException(status_code=500, detail="Feedback directory not found")
    
    # 获取所有反馈文件
    feedback_files = list(FEEDBACK_DIR.glob("*_feedback.md"))
    
    # 提取唯一的学号
    student_ids = set()
    for file_path in feedback_files:
        filename = file_path.stem
        parts = filename.split('_')
        if parts:
            student_ids.add(parts[0])
    
    return {
        "count": len(student_ids),
        "students": sorted(list(student_ids))
    }


def main():
    """主函数 - 启动 FastAPI 服务器"""
    uvicorn.run(
        "main1:app",  # 改为 main1:app
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式下启用热重载
        log_level="info"
    )


if __name__ == "__main__":
    main()
