import os
import sys
import subprocess
import jinja2
from weasyprint import HTML


class PrintService:
    def __init__(self):
        # 模板目录
        template_dir = os.path.join(os.path.dirname(__file__), "../web")
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

    def print_label(self, record: dict) -> bool:
        """
        渲染 web/label.html 模板 -> PDF -> 系统默认打印机
        """
        try:
            # 1. 渲染 HTML
            template = self.env.get_template("label.html")
            html_content = template.render(record=record["record"])
            print(html_content)
            return;
            # 2. 生成 PDF 文件
            pdf_file = os.path.join(os.path.dirname(__file__), "label.pdf")
            HTML(string=html_content).write_pdf(pdf_file)

            # 3. 调用系统默认打印机
            if sys.platform.startswith("win"):
                try:
                    import win32api
                    win32api.ShellExecute(0, "print", pdf_file, None, ".", 0)
                except Exception as e:
                    print("[PrintService] Windows 打印失败:", e)
                    return False
            else:
                proc = subprocess.run(["lp", pdf_file], capture_output=True, text=True)
                if proc.returncode != 0:
                    print("[PrintService] 打印失败:", proc.stderr)
                    return False

            print("[PrintService] 打印成功")
            return True

        except Exception as e:
            print("[PrintService] 打印异常:", e)
            return False