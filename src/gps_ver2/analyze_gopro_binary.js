// analyze_gopro_binary.js
// GoProバイナリデータの詳細解析ツール

const fs = require('fs');
const path = require('path');

const currentDir = __dirname;
const outputDir = path.join(currentDir, 'output');

console.log('GoPro Binary Data Analyzer');
console.log('=============================');

function analyzeGoProBinary(binFile) {
    console.log(`\nAnalyzing: ${binFile}`);
    
    try {
        const data = fs.readFileSync(binFile);
        console.log(`File size: ${data.length} bytes (${(data.length / 1024).toFixed(2)} KB)`);
        
        // 全体の16進数ダンプ（最初の512バイト）
        console.log('\nHex dump (first 512 bytes):');
        const previewSize = Math.min(512, data.length);
        for (let i = 0; i < previewSize; i += 16) {
            const slice = data.subarray(i, Math.min(i + 16, previewSize));
            const hex = Array.from(slice, byte => byte.toString(16).padStart(2, '0')).join(' ');
            const ascii = Array.from(slice, byte => 
                (byte >= 32 && byte <= 126) ? String.fromCharCode(byte) : '.'
            ).join('');
            console.log(`${i.toString(16).padStart(4, '0')}: ${hex.padEnd(47)} | ${ascii}`);
        }
        
        // 既知のGoProタグを検索
        const goProTags = ['DEVC', 'DVID', 'DVNM', 'STRM', 'STNM', 'RMRK', 'SCAL', 'SIUN', 'UNIT', 'TYPE'];
        const gpsRelatedTags = ['GPS5', 'GPSU', 'GPSF', 'GPSP', 'GPSA'];
        const sensorTags = ['ACCL', 'GYRO', 'CORI', 'IORI', 'GRAV', 'WNDM', 'MWET'];
        
        console.log('\nTag Analysis:');
        const allTags = [...goProTags, ...gpsRelatedTags, ...sensorTags];
        const foundTags = [];
        
        allTags.forEach(tag => {
            const tagBuffer = Buffer.from(tag, 'ascii');
            let offset = 0;
            const positions = [];
            
            while (true) {
                const index = data.indexOf(tagBuffer, offset);
                if (index === -1) break;
                positions.push(index);
                offset = index + 1;
                if (positions.length > 10) break; // 最初の10個まで
            }
            
            if (positions.length > 0) {
                foundTags.push({ tag, count: positions.length, positions: positions.slice(0, 5) });
                console.log(`   ${tag}: Found ${positions.length} times at positions [${positions.slice(0, 5).join(', ')}${positions.length > 5 ? '...' : ''}]`);
                
                // 最初の出現位置の前後のデータを表示
                const pos = positions[0];
                const contextStart = Math.max(0, pos - 8);
                const contextEnd = Math.min(data.length, pos + tag.length + 8);
                const context = data.subarray(contextStart, contextEnd);
                const contextHex = Array.from(context, byte => byte.toString(16).padStart(2, '0')).join(' ');
                console.log(`     Context: ${contextHex}`);
            }
        });
        
        // データ構造の推定
        console.log('\n🏗️  Data Structure Analysis:');
        
        // 4バイト境界でのパターン検索
        const patterns = new Map();
        for (let i = 0; i < Math.min(data.length - 4, 1000); i += 4) {
            const pattern = data.subarray(i, i + 4).toString('hex');
            patterns.set(pattern, (patterns.get(pattern) || 0) + 1);
        }
        
        // 頻出パターンを表示
        const sortedPatterns = Array.from(patterns.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        console.log('   Most common 4-byte patterns:');
        sortedPatterns.forEach(([pattern, count]) => {
            if (count > 1) {
                console.log(`     ${pattern}: ${count} times`);
            }
        });
        
        // 文字列の抽出
        console.log('\nReadable Strings:');
        const strings = [];
        let currentString = '';
        
        for (let i = 0; i < data.length; i++) {
            const byte = data[i];
            if (byte >= 32 && byte <= 126) {
                currentString += String.fromCharCode(byte);
            } else {
                if (currentString.length >= 4) {
                    strings.push({ str: currentString, pos: i - currentString.length });
                }
                currentString = '';
            }
        }
        
        // 長い文字列を表示
        const longStrings = strings.filter(s => s.str.length >= 4).slice(0, 20);
        longStrings.forEach(({ str, pos }) => {
            console.log(`   ${pos.toString(16).padStart(4, '0')}: "${str}"`);
        });
        
        // GoProデバイス情報の抽出
        console.log('\nDevice Information:');
        const deviceName = extractStringAfterTag(data, 'DVNM');
        if (deviceName) {
            console.log(`   Device Name: ${deviceName}`);
        }
        
        const firmware = extractStringAfterTag(data, 'FMWR');
        if (firmware) {
            console.log(`   Firmware: ${firmware}`);
        }
        
        // データの保存オプション
        console.log('\nExport Options:');
        console.log(`   Raw binary: ${binFile}`);
        
        // 異なるフォーマットでの保存を試行
        const baseName = path.parse(binFile).name;
        
        // JSON形式でのメタデータ保存
        const metadata = {
            fileSize: data.length,
            foundTags: foundTags,
            deviceName: deviceName,
            firmware: firmware,
            analysis: {
                hasGPMF: data.includes(Buffer.from('GPMF')),
                hasGPS: foundTags.some(t => gpsRelatedTags.includes(t.tag)),
                hasSensors: foundTags.some(t => sensorTags.includes(t.tag)),
                readableStrings: longStrings.slice(0, 10)
            }
        };
        
        const metadataFile = path.join(outputDir, `${baseName}_analysis.json`);
        fs.writeFileSync(metadataFile, JSON.stringify(metadata, null, 2));
        console.log(`   Analysis JSON: ${metadataFile}`);
        
        return metadata;
        
    } catch (error) {
        console.error(`Analysis failed: ${error.message}`);
        return null;
    }
}

function extractStringAfterTag(data, tag) {
    const tagBuffer = Buffer.from(tag, 'ascii');
    const index = data.indexOf(tagBuffer);
    
    if (index === -1) return null;
    
    // タグの後のデータを確認
    const afterTag = index + tag.length;
    if (afterTag >= data.length) return null;
    
    // 文字列長を取得（GoProフォーマットによる）
    // 通常、タグの後に長さ情報がある
    let str = '';
    for (let i = afterTag; i < Math.min(afterTag + 64, data.length); i++) {
        const byte = data[i];
        if (byte >= 32 && byte <= 126) {
            str += String.fromCharCode(byte);
        } else if (str.length > 0) {
            break;
        }
    }
    
    return str.length > 0 ? str : null;
}

// 代替処理方法の提案
function suggestAlternatives(metadata) {
    console.log('\n Alternative Processing Suggestions:');
    
    if (metadata.analysis.hasGPS) {
        console.log('    GPS data detected - try GPS-specific extractors');
    }
    
    if (metadata.analysis.hasSensors) {
        console.log('    Sensor data detected - accelerometer/gyroscope available');
    }
    
    if (metadata.deviceName && metadata.deviceName.includes('Max')) {
        console.log('    GoPro Max detected - may need Max-specific processing');
        console.log('    Try: gopro2gpx with Max-specific options');
        console.log('    Try: different ffmpeg stream mapping');
    }
    
    if (!metadata.analysis.hasGPMF) {
        console.log('     No standard GPMF format detected');
        console.log('    This may be a proprietary format or encrypted data');
        console.log('    Try extracting from different video streams');
    }
    
    console.log('\n Recommended Next Steps:');
    console.log('   1. Try gopro2gpx directly on the .bin file');
    console.log('   2. Extract different streams (0:2, 0:4, 0:5)');
    console.log('   3. Use GoPro Max specific tools if available');
    console.log('   4. Check if video was recorded in a special mode');
}

// メイン実行
function main() {
    const binFile = process.argv[2];
    
    if (!binFile) {
        console.log('Usage: node analyze_gopro_binary.js <binary_file>');
        console.log('');
        console.log('Example:');
        console.log('  node analyze_gopro_binary.js output/GS010678.bin');
        process.exit(1);
    }
    
    const binPath = path.resolve(binFile);
    
    if (!fs.existsSync(binPath)) {
        console.error(` Binary file not found: ${binPath}`);
        process.exit(1);
    }
    
    const metadata = analyzeGoProBinary(binPath);
    
    if (metadata) {
        suggestAlternatives(metadata);
        console.log('\n Analysis completed!');
    } else {
        console.log('\n Analysis failed');
        process.exit(1);
    }
}

main();
