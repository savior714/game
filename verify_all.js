const { execSync } = require('child_process');
const path = require('path');

const scripts = [
    'verify_net_logic.js',
    'korean/verify_korean_engine.js',
    'science/verify_science_engine.js',
    'english/verify_english_engine.js',
    'math/verify_math_engine.js'
];

console.log('🌟 Starting Global Game Engine Verification 🌟');
console.log('==============================================\n');

let failedCount = 0;

scripts.forEach(script => {
    console.log(`Checking: [${script}]...`);
    try {
        const output = execSync(`node ${script}`, { stdio: 'pipe' }).toString();
        // console.log(output);
        console.log(`✅ [${script}] PASS\n`);
    } catch (error) {
        console.error(`❌ [${script}] FAIL`);
        console.error(error.stdout.toString());
        failedCount++;
    }
});

console.log('==============================================');
if (failedCount === 0) {
    console.log('✨ ALL SUBJECTS VERIFIED SUCCESSFULLY! ✨');
    process.exit(0);
} else {
    console.error(`💥 VERIFICATION FAILED: ${failedCount} subject(s) error(s)`);
    process.exit(1);
}
console.log('==============================================\n');
