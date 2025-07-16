import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import shutil
from pathlib import Path

# --- 配置区 ---
# 请根据您的实际情况修改以下路径
EWFEXPORT_PATH = r"..\ewf-tools-win64-main\ewf-tools\ewfexport.exe"  
QEMU_IMG_PATH = r"..\Tools\qemu-img.exe"    
# --- 配置区结束 ---

class E01ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("E01 到 VMDK 转换器")
        self.root.geometry("600x580")
        self.root.resizable(False, False)

        # 样式
        self.style = ttk.Style()
        self.style.configure("TFrame", padding=10, relief="flat")
        self.style.configure("TLabel", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"))
        self.style.configure("TEntry", font=("Segoe UI", 10))
        self.style.configure("TCombobox", font=("Segoe UI", 10))
        self.style.configure("TProgressbar", thickness=15)

        # 主框架
        main_frame = ttk.Frame(root, padding="15 15 15 15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # E01文件路径选择
        path_frame = ttk.LabelFrame(main_frame, text="1. E01 文件路径", padding="10")
        path_frame.pack(fill=tk.X, pady=10)

        self.e01_path_entry = ttk.Entry(path_frame, width=60)
        self.e01_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.browse_button = ttk.Button(path_frame, text="浏览...", command=self.browse_e01_file)
        self.browse_button.pack(side=tk.RIGHT)

        # 输出目录选择
        output_frame = ttk.LabelFrame(main_frame, text="2. 输出目录 (VMDK和VMX将生成在此)", padding="10")
        output_frame.pack(fill=tk.X, pady=10)

        self.output_dir_entry = ttk.Entry(output_frame, width=60)
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.browse_output_button = ttk.Button(output_frame, text="选择目录...", command=self.browse_output_dir)
        self.browse_output_button.pack(side=tk.RIGHT)

        # 操作系统和启动方式选择
        vm_config_frame = ttk.LabelFrame(main_frame, text="3. 虚拟机配置 (用于生成VMX)", padding="10")
        vm_config_frame.pack(fill=tk.X, pady=10)

        # 操作系统类型
        ttk.Label(vm_config_frame, text="操作系统类型:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.os_type_options = [
            "Windows 10 64-bit", "Windows 8 64-bit", "Windows 7 64-bit",
            "Windows XP 32-bit", "Windows 2003 Server 32-bit",
            "Ubuntu 64-bit", "Debian 64-bit", "CentOS 64-bit", "Other Linux 64-bit",
            "Other 64-bit", "Other 32-bit"
        ]
        self.os_type_var = tk.StringVar(root)
        self.os_type_var.set(self.os_type_options[0]) # 默认值
        self.os_type_menu = ttk.Combobox(vm_config_frame, textvariable=self.os_type_var,
                                         values=self.os_type_options, state="readonly", width=30)
        self.os_type_menu.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # 启动方式
        ttk.Label(vm_config_frame, text="启动方式:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.boot_type_options = ["BIOS", "EFI (UEFI)"]
        self.boot_type_var = tk.StringVar(root)
        self.boot_type_var.set(self.boot_type_options[0]) # 默认值
        self.boot_type_menu = ttk.Combobox(vm_config_frame, textvariable=self.boot_type_var,
                                           values=self.boot_type_options, state="readonly", width=30)
        self.boot_type_menu.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # 转换按钮
        self.convert_button = ttk.Button(main_frame, text="开始转换", command=self.start_conversion, style="TButton")
        self.convert_button.pack(pady=20, ipadx=20, ipady=10)

        # 进度条
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=500, mode="determinate", style="TProgressbar")
        self.progress_bar.pack(pady=10)

        # 日志输出
        log_frame = ttk.LabelFrame(main_frame, text="日志输出", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.log_text = tk.Text(log_frame, height=8, state="disabled", font=("Consolas", 9), bg="#f0f0f0")
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text_scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        self.log_text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=self.log_text_scrollbar.set)

        self.initial_dir_set = False # 标记是否已设置初始输出目录

    def log_message(self, message):
        """向日志框输出信息"""
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END) # 自动滚动到底部
        self.log_text.config(state="disabled")
        self.root.update_idletasks() # 立即更新GUI

    def browse_e01_file(self):
        """选择E01文件"""
        file_path = filedialog.askopenfilename(
            title="选择 E01 文件",
            filetypes=[("E01 Files", "*.e01"), ("All Files", "*.*")]
        )
        if file_path:
            self.e01_path_entry.delete(0, tk.END)
            self.e01_path_entry.insert(0, file_path)
            # 自动设置输出目录为E01文件所在目录
            if not self.initial_dir_set:
                output_dir = Path(file_path).parent
                self.output_dir_entry.delete(0, tk.END)
                self.output_dir_entry.insert(0, str(output_dir))
                self.initial_dir_set = True

    def browse_output_dir(self):
        """选择输出目录"""
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, dir_path)
            self.initial_dir_set = True

    def run_command(self, command, description, input_data=None, cwd=None):
        """执行外部命令并记录日志，支持传入输入数据"""
        self.log_message(f"--- 正在执行: {description} ---")
        self.log_message(f"命令: {' '.join(command)}")
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,  # 允许写入标准输入
                stdout=subprocess.PIPE, # 捕获标准输出
                stderr=subprocess.PIPE, # 捕获标准错误
                text=True,              # 以文本模式处理输入输出
                encoding='utf-8',       # 尝试使用UTF-8编码，如果不行再尝试gbk
                errors='replace',       # 编码错误时替换字符
                cwd=cwd                 # 设置工作目录
            )

            # 写入输入数据（如果有）
            stdout, stderr = process.communicate(input=input_data)

            if process.returncode != 0:
                self.log_message(f"错误: {description} 命令执行失败，返回码 {process.returncode}")
                self.log_message("标准输出:\n" + stdout)
                self.log_message("标准错误:\n" + stderr)
                # 尝试用gbk再次解码stderr，因为有些工具可能默认gbk
                try:
                    # 注意：这里是将已解码的字符串重新编码成UTF-8字节，再解码成GBK字符串
                    # 更好的方法是直接尝试不同的解码方式，但因为原始subprocess.run的编码问题，这里保持一致
                    stderr_gbk = stderr.encode('utf-8').decode('gbk', errors='replace')
                    if stderr_gbk != stderr: # 如果gbk解码不同，说明可能是编码问题
                         self.log_message("标准错误 (GBK 解码尝试):\n" + stderr_gbk)
                except Exception:
                    pass

                messagebox.showerror("错误", f"{description} 失败！\n请检查日志获取详情。")
                return False
            else:
                self.log_message("命令执行成功！")
                self.log_message("标准输出:\n" + stdout)
                if stderr:
                    self.log_message("标准错误 (可能包含信息，非错误):\n" + stderr)
                return True
        except FileNotFoundError:
            self.log_message(f"错误: 找不到 {command[0]}。请检查配置中的工具路径是否正确。")
            messagebox.showerror("错误", f"找不到 {command[0]}。\n请检查配置中的工具路径是否正确。")
            return False
        except Exception as e:
            self.log_message(f"执行 {description} 时发生未知错误: {e}")
            messagebox.showerror("错误", f"未知错误: {e}")
            return False

    def generate_vmx_content(self, vmdk_filename, os_type_selected, boot_type_selected):
        """根据选择生成VMX文件内容"""
        # 将用户友好的OS类型映射到VMware的guestOS标识符
        os_type_map = {
            "Windows 10 64-bit": "windows9-64",
            "Windows 8 64-bit": "windows8-64",
            "Windows 7 64-bit": "windows7-64",
            "Windows XP 32-bit": "winxp",
            "Windows 2003 Server 32-bit": "winnetstandard",
            "Ubuntu 64-bit": "ubuntu-64",
            "Debian 64-bit": "debian9-64", # 较新的Debian
            "CentOS 64-bit": "centos7-64", # 较新的CentOS
            "Other Linux 64-bit": "otherlinux-64",
            "Other 64-bit": "other-64",
            "Other 32-bit": "other"
        }
        vmware_guest_os = os_type_map.get(os_type_selected, "other-64")

        # 根据启动方式设置firmware
        firmware_setting = ""
        if boot_type_selected == "EFI (UEFI)":
            firmware_setting = "firmware = \"efi\""

        # VMX 模板
        # 提供了常见的配置，您可以根据需要进行调整
        vmx_content = f"""
.encoding = "GBK"
config.version = "8"
virtualHW.version = "17" # 可以是 10, 11, 12, 14, 15, 16, 17 (对应不同VMware版本)
vmci0.present = "TRUE"
memsize = "4096" # 内存大小，单位MB
numvcpus = "2"   # CPU核心数
displayName = "{Path(vmdk_filename).stem}_converted_vm" # 虚拟机显示名称
guestOS = "{vmware_guest_os}" # 操作系统类型

{firmware_setting} # UEFI 或 BIOS 设置

# 硬盘
ide0:0.fileName = "{vmdk_filename}"
ide0:0.present = "TRUE"
ide0:0.redo = "" # 如果您希望保留快照功能，可以移除此行或设置为"auto"
# scsi0:0.fileName = "{vmdk_filename}" # 如果是SCSI磁盘，请使用此行并注释掉IDE行
# scsi0:0.present = "TRUE"
# scsi0:0.redo = ""
# scsi0.virtualDev = "lsilogic" # LSI Logic for SCSI

# 网络适配器 (NAT模式)
ethernet0.present = "TRUE"
ethernet0.connectionType = "nat"
ethernet0.virtualDev = "e1000" # 或 "vmxnet3" 获取更好性能 (需要安装VMware Tools)
ethernet0.wakeOnPcktRcv = "FALSE"

# USB 控制器
usb.present = "TRUE"
usb.autoConnect.enabled = "TRUE"

# 声音
sound.present = "TRUE"
sound.virtualDev = "hdaudio"

# CD/DVD 驱动器 (自动检测物理驱动器)
ide1:0.present = "TRUE"
ide1:0.deviceType = "atapi-cdrom"
ide1:0.startConnected = "FALSE"
ide1:0.autodetect = "TRUE"

# 其他设置
isolation.tools.hgfs.disable = "TRUE" # 禁用共享文件夹，提高安全性
mks.enable3d = "TRUE" # 启用3D加速
bios.bootdelay = "2000" # 启动时延迟2秒，方便进入BIOS/EFI设置

# 工具
tools.syncTime = "TRUE"
tools.upgrade.policy = "manual"

# 快照 (如果不需要快照，可以禁用)
snapshot.action = "autoCommit"
snapshot.numSnapshots = "0"

"""
        return vmx_content.strip()

    def start_conversion(self):
        """开始整个转换流程"""
        e01_path_str = self.e01_path_entry.get().strip()
        output_dir_str = self.output_dir_entry.get().strip()
        os_type_selected = self.os_type_var.get()
        boot_type_selected = self.boot_type_var.get()

        if not e01_path_str:
            messagebox.showwarning("输入错误", "请选择 E01 文件。")
            return
        if not output_dir_str:
            messagebox.showwarning("输入错误", "请选择输出目录。")
            return
        if not Path(EWFEXPORT_PATH).is_file():
            messagebox.showerror("工具错误", f"找不到 ewfexport.exe。请检查配置中的路径: {EWFEXPORT_PATH}")
            return
        if not Path(QEMU_IMG_PATH).is_file():
            messagebox.showerror("工具错误", f"找不到 qemu-img.exe。请检查配置中的路径: {QEMU_IMG_PATH}")
            return

        e01_path = Path(e01_path_str)
        output_dir = Path(output_dir_str)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 基于E01文件名生成中间RAW和最终VMDK的文件名
        base_name = e01_path.stem # 获取不带扩展名的文件名
        raw_path = output_dir / f"{base_name}.raw" # 完整的raw文件路径
        vmdk_path = output_dir / f"{base_name}.vmdk"
        vmx_path = output_dir / f"{base_name}.vmx"

        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END) # 清空日志
        self.log_text.config(state="disabled")
        self.log_message("--- 开始转换流程 ---")
        self.progress_bar["value"] = 0
        self.convert_button.config(state="disabled") # 禁用按钮防止重复点击

        try:
            # 1. 调用 ewfexport.exe 将 E01 转换为 RAW
            self.log_message(f"阶段1/3: 正在将 E01 转换为 RAW ({raw_path})...")
            # ewfexport 的输入数据：
            # 1. 格式选择 (raw) - 直接回车，因为 -f raw 已经指定
            # 2. 目标文件名 (Windows_Server) - raw_path.stem
            # 3. 段大小 (0 B) - 回车
            # 4. 起始偏移 (0) - 回车
            # 5. 导出字节数 (全部) - 回车
            ewf_input_data = f"\n{raw_path.stem}\n\n\n\n" # 5个换行符

            ewf_command = [
                EWFEXPORT_PATH,
                str(e01_path),
                "-f", "raw",  # 指定输出格式为 raw
                # 注意：这里不再包含 -o 参数，我们将通过 stdin 提供文件名
            ]
            # 运行 ewfexport，并将工作目录设置为输出目录，同时提供输入数据
            if not self.run_command(ewf_command, "E01 到 RAW 转换", input_data=ewf_input_data, cwd=output_dir):
                raise Exception("E01 转换失败")
            self.progress_bar["value"] = 33

            # 2. 调用 qemu-img.exe 将 RAW 转换为 VMDK
            self.log_message(f"阶段2/3: 正在将 RAW 转换为 VMDK ({vmdk_path})...")
            qemu_command = [
                QEMU_IMG_PATH,
                "convert",
                "-f", "raw",
                "-O", "vmdk",
                str(raw_path),
                str(vmdk_path)
            ]
            if not self.run_command(qemu_command, "RAW 到 VMDK 转换"):
                raise Exception("RAW 转换失败")
            self.progress_bar["value"] = 66

            # 3. 生成 VMX 文件
            self.log_message(f"阶段3/3: 正在生成 VMX 文件 ({vmx_path})...")
            vmx_content = self.generate_vmx_content(vmdk_path.name, os_type_selected, boot_type_selected)
            try:
                with open(vmx_path, "w", encoding="utf-8") as f:
                    f.write(vmx_content)
                self.log_message(f"VMX 文件已成功生成: {vmx_path}")
            except Exception as e:
                self.log_message(f"错误: 生成 VMX 文件失败: {e}")
                raise Exception("VMX 生成失败")
            self.progress_bar["value"] = 90

            # 4. 删除中间产物 RAW 文件
            self.log_message(f"正在删除中间产物 RAW 文件 ({raw_path})...")
            try:
                os.remove(raw_path)
                self.log_message("RAW 文件删除成功。")
            except OSError as e:
                self.log_message(f"警告: 删除 RAW 文件失败: {e}")
                messagebox.showwarning("警告", f"删除中间产物 RAW 文件失败。\n请手动删除: {raw_path}")
            self.progress_bar["value"] = 100

            self.log_message("--- 所有操作完成！ ---")
            messagebox.showinfo("完成", f"E01 文件已成功转换为 VMDK，并生成 VMX 文件！\n\nVMDK: {vmdk_path}\nVMX: {vmx_path}")

        except Exception as e:
            self.log_message(f"流程中断: {e}")
            self.log_message("--- 转换流程失败 ---")
        finally:
            self.convert_button.config(state="normal") # 重新启用按钮

if __name__ == "__main__":
    root = tk.Tk()
    app = E01ConverterApp(root)
    root.mainloop()
