# Bumped from golang:1.17: the (unpinned) instana/go-sensor dependency now
# requires a newer Go toolchain. GOTOOLCHAIN=auto lets Go fetch a newer
# toolchain automatically if future dependency bumps require it.
FROM golang:1.24
ENV GOTOOLCHAIN=auto

WORKDIR /go/src/app

COPY *.go .

RUN go mod init dispatch && go get
RUN go install

CMD dispatch
