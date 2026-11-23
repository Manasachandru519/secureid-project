// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Stores only a commitment and status. Never put personal identity data on-chain.
contract IdentityRegistry {
    struct Record {
        bytes32 commitment;
        uint8 status; // 0=pending, 1=verified, 2=revoked
        uint256 updatedAt;
    }
    mapping(bytes32 => Record) private records;
    address public owner;
    event IdentityRegistered(bytes32 indexed identityId, bytes32 commitment);
    event StatusChanged(bytes32 indexed identityId, uint8 status);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only administrator");
        _;
    }
    constructor() { owner = msg.sender; }

    function registerIdentity(bytes32 identityId, bytes32 commitment) external onlyOwner {
        require(records[identityId].updatedAt == 0, "Already registered");
        records[identityId] = Record(commitment, 0, block.timestamp);
        emit IdentityRegistered(identityId, commitment);
    }
    function updateStatus(bytes32 identityId, uint8 status) external onlyOwner {
        require(records[identityId].updatedAt != 0, "Unknown identity");
        require(status <= 2, "Invalid status");
        records[identityId].status = status;
        records[identityId].updatedAt = block.timestamp;
        emit StatusChanged(identityId, status);
    }
    function getRecord(bytes32 identityId) external view returns (bytes32, uint8, uint256) {
        Record memory r = records[identityId];
        return (r.commitment, r.status, r.updatedAt);
    }
}
