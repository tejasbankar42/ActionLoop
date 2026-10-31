/* Deploys ActionLoopAuditRegistry and records the result in deployments/<network>.json.
 *
 *   npm run deploy:testnet              # MST Testnet (chain 91562037)
 *   npm run deploy:mainnet              # MST Mainnet (chain 4646) - asks for typed confirmation
 *
 * Optional env: AUDIT_SUBMITTER_ADDRESS - backend relayer address to authorize at deploy time.
 */
const fs = require("fs");
const path = require("path");
const readline = require("readline");
const hre = require("hardhat");

const EXPECTED_CHAIN = { mstTestnet: 91562037n, mstMainnet: 4646n, hardhat: 31337n };
const EXPLORER = { mstTestnet: "https://testnet.mstscan.com", mstMainnet: "https://mstscan.com" };

function ask(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => rl.question(question, (a) => { rl.close(); resolve(a); }));
}

async function main() {
  const net = hre.network.name;
  const { ethers } = hre;
  const [deployer] = await ethers.getSigners();
  if (!deployer) throw new Error("DEPLOYER_PRIVATE_KEY is not set in contracts/.env");

  const chainId = (await ethers.provider.getNetwork()).chainId;
  if (EXPECTED_CHAIN[net] !== undefined && chainId !== EXPECTED_CHAIN[net]) {
    throw new Error(`RPC reports chain ${chainId}, expected ${EXPECTED_CHAIN[net]} for ${net}`);
  }

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`Network:   ${net} (chain ${chainId})`);
  console.log(`Deployer:  ${deployer.address}`);
  console.log(`Balance:   ${ethers.formatEther(balance)}`);
  if (balance === 0n) throw new Error("Deployer has no balance. Claim tMSTC at https://faucet.mstblockchain.com");

  if (net === "mstMainnet") {
    const answer = await ask('This deploys to MST MAINNET with real funds. Type "yes, deploy to mainnet": ');
    if (answer.trim() !== "yes, deploy to mainnet") {
      console.log("Aborted.");
      return;
    }
  }

  const submitter = process.env.AUDIT_SUBMITTER_ADDRESS || ethers.ZeroAddress;
  const Factory = await ethers.getContractFactory("ActionLoopAuditRegistry");
  const contract = await Factory.deploy(submitter);
  const deployTx = contract.deploymentTransaction();
  console.log(`Deploy tx: ${deployTx.hash}`);
  const receipt = await deployTx.wait();
  if (receipt.status !== 1) throw new Error("Deployment transaction reverted");
  const address = await contract.getAddress();

  const record = {
    network: net,
    chainId: Number(chainId),
    contract: "ActionLoopAuditRegistry",
    address,
    deployer: deployer.address,
    initialSubmitter: submitter,
    deployTxHash: deployTx.hash,
    blockNumber: receipt.blockNumber,
    explorer: EXPLORER[net] ? `${EXPLORER[net]}/address/${address}` : null,
    deployedAt: new Date().toISOString(),
  };
  const dir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `${net}.json`), JSON.stringify(record, null, 2));
  console.log(`Deployed:  ${address} (block ${receipt.blockNumber})`);
  if (record.explorer) console.log(`Explorer:  ${record.explorer}`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
