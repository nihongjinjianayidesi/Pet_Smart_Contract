package main

import (
	"log"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

func main() {
	chaincode, err := contractapi.NewChaincode(&SmartContract{})
	if err != nil {
		log.Panicf("创建链码失败: %v", err)
	}

	if err := chaincode.Start(); err != nil {
		log.Panicf("启动链码失败: %v", err)
	}
}

