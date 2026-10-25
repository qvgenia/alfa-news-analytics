
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agent.orchestrator import AgentOrchestrator

router = APIRouter(tags=["assistant"])
orchestrator = AgentOrchestrator()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=5000)


class AskResponse(BaseModel):
    answer: str
    status: str


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    result = orchestrator.ask(request.question)
    return AskResponse(
        answer=result.answer,
        status=result.status,
    )
