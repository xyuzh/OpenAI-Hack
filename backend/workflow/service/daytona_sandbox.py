import uuid
import asyncio
from typing import List

from daytona import (
    AsyncDaytona,
    AsyncSandbox,
    FileUpload as DaytonaFileUpload,
    SessionExecuteRequest,
    CreateSandboxFromSnapshotParams,
)
from daytona_api_client_async.models.replace_result import ReplaceResult
from daytona_api_client_async.models.sandbox_state import SandboxState
from workflow.service.schema import BashOps
from workflow.service.sandbox_base import SandboxBase, FileItem
from workflow.storage.user_repo import UserRepo

from workflow.schema.user import User
from workflow.core.logger import usebase_logger as logger


class DaytonaSandbox(SandboxBase):
    def __init__(self):
        self.sandbox: AsyncSandbox | None = None
        self.daytona = AsyncDaytona()

    @classmethod
    async def init(cls, user: User, daytona_image: str, user_repo: UserRepo):
        self = cls()
        try:
            if user.sandbox_id is None:
                raise Exception("Sandbox id is not set")
            self.sandbox = await self.daytona.get(user.sandbox_id)
            if self.sandbox.state != SandboxState.STARTED:
                logger.info(f"Sandbox {user.sandbox_id} is not started, starting it")
                await self.sandbox.start()
        except Exception as e:
            logger.info(f"Sandbox {user.sandbox_id} not found, creating new sandbox")

            # Create a new sandbox
            if self.sandbox:
                await self.sandbox.delete()
            try:
                self.sandbox = await self.daytona.create(
                    CreateSandboxFromSnapshotParams(snapshot=daytona_image, public=True)
                )
            except Exception as e:
                logger.error(f"Error creating sandbox: {e}")
                raise e
        if user.sandbox_id != self.sandbox.id:
            await user_repo.update_sandbox(user.id, self.sandbox.id)
            user.sandbox_id = self.sandbox.id
        return self

    async def upload_files(self, files: List[FileItem]) -> None:
        if not self.sandbox:
            raise Exception("Sandbox not initialized")

        upload_files = [
            DaytonaFileUpload(destination=file.path, source=file.content.encode())
            for file in files
        ]
        try:
            await self.sandbox.fs.upload_files(upload_files)
        except Exception as e:
            logger.error(f"Error uploading files: {e}")
            raise e

    async def download_files(self, files_path: List[str]) -> List[FileItem]:
        if not self.sandbox:
            raise Exception("Sandbox not initialized")

        try:
            downloaded_files = await asyncio.gather(
                *[self.sandbox.fs.download_file(file_path) for file_path in files_path]
            )
            downloaded_files = [
                FileItem(content=file.decode(), path=files_path[i])
                for i, file in enumerate(downloaded_files)
            ]
            return downloaded_files
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise e

    async def run_bash(self, bash_ops: BashOps, cwd: str) -> str:
        if not self.sandbox:
            raise Exception("Sandbox not initialized")

        try:
            res = await self.sandbox.process.exec(
                bash_ops.cmd,
                cwd=cwd,
                env=bash_ops.env,
                timeout=bash_ops.timeout,
            )
            return res.result
        except Exception as e:
            logger.error(f"Error executing bash command: {e}")
            raise e

    async def run_bash_async(self, cmd: str, cwd: str, session_id: str = '') -> str:
        if not self.sandbox:
            raise Exception("Sandbox not initialized")

        if session_id == '':
            session_id = uuid.uuid4().hex
        cmd = f'cd {cwd} && {cmd}'
        bash_result: list[str] = []

        def log_handler(logs):
            if logs and logs != '\\x00':
                bash_result.append(logs)

        try:
            await self.sandbox.process.create_session(session_id=session_id)
        except Exception as e:
            logger.info(f"Session create failed {e}")
            raise e

        try:
            res = await self.sandbox.process.execute_session_command(
                session_id=session_id,
                req=SessionExecuteRequest(
                    command=cmd,
                    run_async=True,
                ),
            )
        except Exception as e:
            logger.error(f"Error executing async bash command: {e}")
            raise e

        # Create a task for the log streaming and handle network errors properly
        log_task = None
        try:
            log_task = asyncio.create_task(
                self.sandbox.process.get_session_command_logs_async(
                    session_id=session_id,
                    command_id=res.cmd_id if res.cmd_id else "",
                    on_logs=log_handler,
                )
            )

            await asyncio.wait_for(log_task, timeout=10)
        except asyncio.TimeoutError:
            pass
        finally:
            if log_task and not log_task.done():
                log_task.cancel()
                try:
                    await log_task
                finally:
                    pass

        bash_result_str = '\n'.join(bash_result).replace('\x00', '')
        logger.info(f"Logged result of a long running command {bash_result_str}")
        return bash_result_str

    async def close(self) -> None:
        """Close/cleanup the sandbox resources"""
        if self.sandbox:
            try:
                await self.sandbox.stop()
                logger.info("Daytona sandbox deleted successfully")
            except Exception as e:
                logger.warning(f"Error deleting Daytona sandbox: {e}")

    async def file_edit(self, path: str, pattern: str, new_value: str) -> ReplaceResult:
        if not self.sandbox:
            raise Exception("Sandbox not initialized")

        try:
            result = await self.sandbox.fs.replace_in_files(
                files=[path], pattern=pattern, new_value=new_value
            )
            return result[0]
        except Exception as e:
            logger.error(f"Error editing file: {e}")
            raise e
