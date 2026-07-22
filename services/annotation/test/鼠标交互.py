import cv2
import torch
from ultralytics import SAM
import os

class SAM3Interactive:
    def __init__(self, model_path, image_path):
        # 1. 加载模型 (只执行一次)
        print(f"🚀 [初始化] 正在加载模型: {model_path}...")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"❌ 模型文件不存在: {model_path}")
        self.model = SAM(model_path)
        
        # 检测设备
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔌 [设备] 运行在: {self.device}")

        # 2. 加载图片 (只执行一次)
        print(f"📂 [加载] 正在读取图片: {image_path}")
        self.original_image = cv2.imread(image_path)
        if self.original_image is None:
            raise ValueError(f"❌ 无法读取图片: {image_path}")
            
        # 用于显示的副本
        self.image = self.original_image.copy()
        
        # 存储点的容器
        self.points = []
        self.labels = []

    def mouse_callback(self, event, x, y, flags, param):
        """鼠标事件处理"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # 左键：前景 (绿色点)
            self.points.append([x, y])
            self.labels.append(1)
            cv2.circle(self.image, (x, y), 8, (0, 255, 0), -1)
            print(f"✅ 添加前景点: ({x}, {y})")
            
        elif event == cv2.EVENT_RBUTTONDOWN:
            # 右键：背景 (红色点)
            self.points.append([x, y])
            self.labels.append(0)
            cv2.circle(self.image, (x, y), 8, (0, 0, 255), -1)
            print(f"🚫 添加背景点: ({x}, {y})")

    def segment(self):
        """执行分割"""
        if len(self.points) == 0:
            print("⚠️ 请先点击添加点！")
            return

        print(f"⚙️ [推理] 正在处理 {len(self.points)} 个点...")
        
        # 3. 根据点分割 (反复执行)
        results = self.model.predict(
            source=self.original_image,
            points=self.points,
            labels=self.labels,
            device=self.device,
            verbose=False
        )

        # 显示结果
        for result in results:
            annotated = result.plot()
            cv2.imshow("Segmentation Result", annotated)
            
        print("✅ 推理完成")

    def reset(self):
        """重置画布"""
        self.points = []
        self.labels = []
        self.image = self.original_image.copy()
        print("🔄 已重置")

    def run(self):
        """主循环"""
        cv2.namedWindow("SAM 3 Interactive")
        cv2.setMouseCallback("SAM 3 Interactive", self.mouse_callback)

        print("\n" + "="*40)
        print("🎮 操作指南:")
        print("🖱️ 左键: 添加前景点 (绿色)")
        print("🖱️ 右键: 添加背景点 (红色)")
        print("⌨️  's': 执行分割")
        print("⌨️  'r': 重置清空")
        print("⌨️  'q': 退出")
        print("="*40 + "\n")

        while True:
            cv2.imshow("SAM 3 Interactive", self.image)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('r'):
                self.reset()
            elif key == ord('s'):
                self.segment()

        cv2.destroyAllWindows()

# ================= 运行入口 =================
if __name__ == "__main__":
    # 配置路径

    MODEL_PATH = "D:/project/ai/ai-annotation-studio-service/test/sam3.pt"
    IMAGE_PATH = "D:/project/ai/ai-annotation-studio-service/test/images/ScreenShot_2025-12-26_151030_700.png"
    try:
        app = SAM3Interactive(MODEL_PATH, IMAGE_PATH)
        app.run()
    except Exception as e:
        print(f"❌ 错误: {e}")