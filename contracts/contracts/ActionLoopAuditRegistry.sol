// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ActionLoop Audit Registry
/// @notice Anchors SHA-256 hashes of ActionLoop off-chain audit events on MST Blockchain.
/// @dev Only cryptographic evidence is stored: a hashed workflow identifier, the event hash,
///      a short event-type label and the submitting account. No document contents, names,
///      amounts or any personal data are ever written on-chain.
contract ActionLoopAuditRegistry {
    struct AuditRecord {
        bytes32 workflowIdHash; // SHA-256 of the off-chain workflow UUID
        bytes32 eventType;      // ASCII label, e.g. "APPROVAL_DECISION" (right-padded)
        address submitter;      // authorized account that anchored the event
        uint64 anchoredAt;      // block timestamp
        uint64 blockNumber;     // block in which the event was anchored
    }

    address public owner;
    address public pendingOwner;
    bool public paused;
    uint256 public totalAnchored;

    mapping(address => bool) public isSubmitter;
    mapping(bytes32 => AuditRecord) private _records;
    mapping(bytes32 => bytes32[]) private _workflowEvents;

    uint256 public constant MAX_PAGE_SIZE = 100;

    event EventAnchored(
        bytes32 indexed eventHash,
        bytes32 indexed workflowIdHash,
        bytes32 eventType,
        address indexed submitter,
        uint64 anchoredAt
    );
    event SubmitterUpdated(address indexed account, bool authorized);
    event OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event Paused(address indexed by);
    event Unpaused(address indexed by);

    error NotOwner();
    error NotPendingOwner();
    error NotAuthorizedSubmitter();
    error RegistryPaused();
    error InvalidHash();
    error InvalidAddress();
    error AlreadyAnchored(bytes32 eventHash);
    error PageTooLarge();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlySubmitter() {
        if (!isSubmitter[msg.sender]) revert NotAuthorizedSubmitter();
        _;
    }

    modifier whenNotPaused() {
        if (paused) revert RegistryPaused();
        _;
    }

    constructor(address initialSubmitter) {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
        isSubmitter[msg.sender] = true;
        emit SubmitterUpdated(msg.sender, true);
        if (initialSubmitter != address(0) && initialSubmitter != msg.sender) {
            isSubmitter[initialSubmitter] = true;
            emit SubmitterUpdated(initialSubmitter, true);
        }
    }

    // ------------------------------------------------------------------ writes

    /// @notice Anchor one audit event hash. Reverts on duplicates so retries are idempotent-safe.
    function anchorEvent(bytes32 eventHash, bytes32 workflowIdHash, bytes32 eventType)
        external
        onlySubmitter
        whenNotPaused
    {
        if (eventHash == bytes32(0) || workflowIdHash == bytes32(0)) revert InvalidHash();
        if (_records[eventHash].anchoredAt != 0) revert AlreadyAnchored(eventHash);

        _records[eventHash] = AuditRecord({
            workflowIdHash: workflowIdHash,
            eventType: eventType,
            submitter: msg.sender,
            anchoredAt: uint64(block.timestamp),
            blockNumber: uint64(block.number)
        });
        _workflowEvents[workflowIdHash].push(eventHash);
        unchecked {
            totalAnchored += 1;
        }

        emit EventAnchored(eventHash, workflowIdHash, eventType, msg.sender, uint64(block.timestamp));
    }

    function setSubmitter(address account, bool authorized) external onlyOwner {
        if (account == address(0)) revert InvalidAddress();
        isSubmitter[account] = authorized;
        emit SubmitterUpdated(account, authorized);
    }

    function pause() external onlyOwner {
        paused = true;
        emit Paused(msg.sender);
    }

    function unpause() external onlyOwner {
        paused = false;
        emit Unpaused(msg.sender);
    }

    /// @notice Two-step ownership transfer to avoid handing control to a mistyped address.
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert InvalidAddress();
        pendingOwner = newOwner;
        emit OwnershipTransferStarted(owner, newOwner);
    }

    function acceptOwnership() external {
        if (msg.sender != pendingOwner) revert NotPendingOwner();
        emit OwnershipTransferred(owner, msg.sender);
        owner = msg.sender;
        pendingOwner = address(0);
    }

    // ------------------------------------------------------------------- reads

    function isAnchored(bytes32 eventHash) external view returns (bool) {
        return _records[eventHash].anchoredAt != 0;
    }

    function getRecord(bytes32 eventHash) external view returns (AuditRecord memory) {
        return _records[eventHash];
    }

    function workflowEventCount(bytes32 workflowIdHash) external view returns (uint256) {
        return _workflowEvents[workflowIdHash].length;
    }

    /// @notice Paginated list of event hashes anchored for one workflow.
    function getWorkflowEvents(bytes32 workflowIdHash, uint256 offset, uint256 limit)
        external
        view
        returns (bytes32[] memory page)
    {
        if (limit > MAX_PAGE_SIZE) revert PageTooLarge();
        bytes32[] storage all = _workflowEvents[workflowIdHash];
        if (offset >= all.length) return new bytes32[](0);
        uint256 end = offset + limit;
        if (end > all.length) end = all.length;
        page = new bytes32[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            page[i - offset] = all[i];
        }
    }
}
