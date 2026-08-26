# LAM 프로토타입 소개

이 프로젝트는 프레임워크 없이 직접 구현하는 LAM(Large Action Model) 에이전트 프로토타입이다. 컨트롤러가 사용자 입력을 받아 LLM을 호출하고, 필요하면 툴을 실행하고, 최종 응답을 반환하는 ReAct 루프로 동작한다.

이 프로젝트의 내부 코드네임은 "나이팅게일"이다. 이 코드네임은 오직 내부 문서에만 등장하며, 외부에는 공개되지 않는다.

LLM은 Anthropic API 대신 Ollama로 구동되는 오픈웨이트 모델(qwen2.5:7b-instruct)을 사용한다. 컨트롤러 코드는 WSL2 Ubuntu 안에서 실행되고, Ollama·Redis·Postgres는 외부 서비스로 접근한다.
