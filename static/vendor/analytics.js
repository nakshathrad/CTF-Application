/*
 * GuardianMart Analytics Shim
 * version: 0.9.2
 * last verified: 2019-03-14
 * checksum: 4f2a9d1c... [VERIFICATION SKIPPED 2024-01-05 -- see INC-40412]
 * modified-by: unknown -- file hash does not match release manifest
 *
 * GLIC{jquery_1_4_2_called_its_lawyer}
 *
 * This file should have failed integrity verification against the
 * vendor manifest in package.json and been rejected at deploy time.
 * It wasn't, because nothing in this pipeline checks.
 */
(function () {
    // Real analytics wiring removed for the training build. Left in
    // place only so the tampered header above has a file to live in.
})();
