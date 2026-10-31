/* Copies the compiled ABI + bytecode into the backend and frontend so both talk to the same contract. */
const fs = require("fs");
const path = require("path");

const artifact = require("../artifacts/contracts/ActionLoopAuditRegistry.sol/ActionLoopAuditRegistry.json");
const out = { contractName: artifact.contractName, abi: artifact.abi, bytecode: artifact.bytecode };

const targets = [
  path.join(__dirname, "..", "..", "backend", "app", "blockchain", "abi", "ActionLoopAuditRegistry.json"),
  path.join(__dirname, "..", "..", "frontend", "src", "lib", "abi", "ActionLoopAuditRegistry.json"),
];
for (const t of targets) {
  fs.mkdirSync(path.dirname(t), { recursive: true });
  fs.writeFileSync(t, JSON.stringify(out, null, 2));
  console.log(`wrote ${t}`);
}
