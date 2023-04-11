FROM python:3.10

# Install linux dependencies
RUN apt-get update && apt-get install -y libssl-dev

RUN apt-get update && apt-get install -y \
    npm

RUN npm install -g ganache-cli

RUN useradd -m -s /bin/bash -u 1000 brownie
RUN mkdir /workspace && chown 1000:1000 /workspace

RUN pip install --upgrade pip cython && pip install --upgrade cytoolz eth-brownie
USER 1000:1000
WORKDIR /workspace

COPY brownie-config.yaml /home/brownie


RUN . /home/brownie/.profile && brownie init && echo "pragma solidity ^0.8.0; contract Lorem {}" >> contracts/lorem.sol && brownie compile

ENTRYPOINT ["bash", "-l", "-c"]
CMD ["brownie test"]
