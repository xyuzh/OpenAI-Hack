import asyncio
from typing import Optional, List

from e2b import AsyncSandbox
from workflow.service.schema import BashOps
from workflow.service.sandbox_base import SandboxBase, FileItem

from workflow.schema.user import User
from workflow.core.logger import usebase_logger as logger


class E2BSandbox(SandboxBase):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.sandbox: Optional[AsyncSandbox] = None

    @classmethod
    async def init(cls, api_key: str, user: User, e2b_template_id: Optional[str] = None):
        self = cls(api_key)
        try:
            if user.sandbox_id:
                self.sandbox = await AsyncSandbox.resume(api_key=api_key, sandbox_id=user.sandbox_id)
                logger.info(f"Connected to E2B sandbox: {user.sandbox_id}")
            else:
                raise Exception("No sandbox ID found, creating new sandbox")
        except Exception as e:
            # TODO(SAVE_SANDBOX_ID): save sandbox id to user if needed
            self.sandbox = await AsyncSandbox.create(
                template=e2b_template_id,
                api_key=api_key,
            )
            logger.info(f"Created new E2B sandbox: {self.sandbox.sandbox_id}")
        return self

    async def upload_files(self, files: List[FileItem]) -> None:
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized")
        
        try:
            # Write files one by one since WriteEntry structure is unclear
            for file in files:
                await self.sandbox.files.write(path=file.path, data=file.content)
            logger.info(f"Uploaded {len(files)} files to E2B sandbox")
        except Exception as e:
            logger.error(f"Error uploading files: {e}")
            raise e

    async def download_files(self, files_path: List[str]) -> List[FileItem]:
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized")
        
        try:
            downloaded_files = []
            for file_path in files_path:
                try:
                    content = await self.sandbox.files.read(file_path, format="text")
                    downloaded_files.append(FileItem(path=file_path, content=content))
                except Exception as e:
                    logger.warning(f"Could not download file {file_path}: {e}")
                    # Continue with other files
                    continue
            return downloaded_files
        except Exception as e:
            logger.error(f"Error downloading files: {e}")
            raise e

    async def run_bash(self, bash_ops: BashOps, cwd: str) -> str:
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized")
        
        try:
            # Construct the full command with cd to the working directory
            full_command = f"cd {cwd} && {bash_ops.cmd}"
            
            # Run the command
            result = await self.sandbox.commands.run(cmd=full_command, envs=bash_ops.env, timeout=bash_ops.timeout)
            
            # Return stdout output (assuming result has stdout attribute)
            if result.exit_code == 0:
                return result.stdout
            else:
                return result.stderr
        except Exception as e:
            logger.error(f"Error running bash command: {e}")
            raise e

    async def run_bash_async(self, cmd: str, cwd: str, session_id: str = '') -> str:
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized")
        
        try:
            result_handler = await self.sandbox.commands.run(cmd=cmd, cwd=cwd, background=True)
            await asyncio.sleep(10)
            if result_handler.error:
                return f'Error: {result_handler.error}'
            return result_handler.stdout
        except Exception as e:
            logger.error(f"Error running bash command: {e}")
            raise e

    async def close(self) -> None:
        """Kill the sandbox to free resources"""
        if self.sandbox:
            try:
                await self.sandbox.pause()
                logger.info("E2B sandbox killed successfully")
            except Exception as e:
                logger.warning(f"Error killing E2B sandbox: {e}")
                raise e
