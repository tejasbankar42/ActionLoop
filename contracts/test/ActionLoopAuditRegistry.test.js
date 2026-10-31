const { expect } = require("chai");
const { ethers } = require("hardhat");

const sha = (s) => ethers.sha256(ethers.toUtf8Bytes(s));
const label = (s) => ethers.encodeBytes32String(s);

describe("ActionLoopAuditRegistry", function () {
  let registry, owner, relayer, outsider, newOwner;

  beforeEach(async function () {
    [owner, relayer, outsider, newOwner] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("ActionLoopAuditRegistry");
    registry = await Factory.deploy(relayer.address);
    await registry.waitForDeployment();
  });

  it("sets owner and initial submitters on deployment", async function () {
    expect(await registry.owner()).to.equal(owner.address);
    expect(await registry.isSubmitter(owner.address)).to.equal(true);
    expect(await registry.isSubmitter(relayer.address)).to.equal(true);
    expect(await registry.isSubmitter(outsider.address)).to.equal(false);
  });

  it("anchors an event, emits EventAnchored and stores the record", async function () {
    const eventHash = sha("event-1");
    const wf = sha("workflow-1");
    await expect(registry.connect(relayer).anchorEvent(eventHash, wf, label("APPROVAL_DECISION")))
      .to.emit(registry, "EventAnchored");

    expect(await registry.isAnchored(eventHash)).to.equal(true);
    expect(await registry.totalAnchored()).to.equal(1n);
    const rec = await registry.getRecord(eventHash);
    expect(rec.workflowIdHash).to.equal(wf);
    expect(rec.submitter).to.equal(relayer.address);
    expect(ethers.decodeBytes32String(rec.eventType)).to.equal("APPROVAL_DECISION");
    expect(rec.anchoredAt).to.be.greaterThan(0n);
  });

  it("rejects duplicate event registration", async function () {
    const eventHash = sha("dup");
    await registry.anchorEvent(eventHash, sha("wf"), label("X"));
    await expect(registry.anchorEvent(eventHash, sha("wf"), label("X")))
      .to.be.revertedWithCustomError(registry, "AlreadyAnchored")
      .withArgs(eventHash);
    expect(await registry.totalAnchored()).to.equal(1n);
  });

  it("rejects unauthorized submitters", async function () {
    await expect(registry.connect(outsider).anchorEvent(sha("e"), sha("w"), label("X")))
      .to.be.revertedWithCustomError(registry, "NotAuthorizedSubmitter");
  });

  it("rejects zero hashes", async function () {
    await expect(registry.anchorEvent(ethers.ZeroHash, sha("w"), label("X")))
      .to.be.revertedWithCustomError(registry, "InvalidHash");
    await expect(registry.anchorEvent(sha("e"), ethers.ZeroHash, label("X")))
      .to.be.revertedWithCustomError(registry, "InvalidHash");
  });

  it("returns false for hashes never anchored", async function () {
    expect(await registry.isAnchored(sha("never"))).to.equal(false);
  });

  it("lets only the owner manage submitters", async function () {
    await expect(registry.connect(outsider).setSubmitter(outsider.address, true))
      .to.be.revertedWithCustomError(registry, "NotOwner");
    await registry.setSubmitter(outsider.address, true);
    await registry.connect(outsider).anchorEvent(sha("e2"), sha("w"), label("X"));
    await registry.setSubmitter(outsider.address, false);
    await expect(registry.connect(outsider).anchorEvent(sha("e3"), sha("w"), label("X")))
      .to.be.revertedWithCustomError(registry, "NotAuthorizedSubmitter");
  });

  it("blocks anchoring while paused", async function () {
    await registry.pause();
    await expect(registry.anchorEvent(sha("p"), sha("w"), label("X")))
      .to.be.revertedWithCustomError(registry, "RegistryPaused");
    await registry.unpause();
    await registry.anchorEvent(sha("p"), sha("w"), label("X"));
  });

  it("paginates events per workflow", async function () {
    const wf = sha("wf-page");
    for (let i = 0; i < 5; i++) await registry.anchorEvent(sha(`e${i}`), wf, label("X"));
    expect(await registry.workflowEventCount(wf)).to.equal(5n);
    const page = await registry.getWorkflowEvents(wf, 1, 3);
    expect(page.length).to.equal(3);
    expect(page[0]).to.equal(sha("e1"));
    expect((await registry.getWorkflowEvents(wf, 10, 3)).length).to.equal(0);
    await expect(registry.getWorkflowEvents(wf, 0, 101))
      .to.be.revertedWithCustomError(registry, "PageTooLarge");
  });

  it("transfers ownership in two steps", async function () {
    await registry.transferOwnership(newOwner.address);
    expect(await registry.owner()).to.equal(owner.address);
    await expect(registry.connect(outsider).acceptOwnership())
      .to.be.revertedWithCustomError(registry, "NotPendingOwner");
    await registry.connect(newOwner).acceptOwnership();
    expect(await registry.owner()).to.equal(newOwner.address);
  });
});
