// gopro_360_to_csv.js
// .360動画から直接CSVファイルを生成する統合ツール

const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

const currentDir = __dirname;
const workspaceRoot = path.join(currentDir, '..', '..');
const includeDir = path.join(workspaceRoot, 'include');
const moviesDir = path.join(workspaceRoot, 'movies');
const outputDir = path.join(currentDir, 'output');

console.log(' GoPro .360 to CSV Converter');
console.log('==============================');

// 出力ディレクトリの作成
if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

// FFmpegのパス検索
function findFFmpeg() {
    const possiblePaths = [
        path.join(includeDir, 'ffmpeg', 'ffmpeg'),
        path.join(includeDir, 'ffmpeg', 'bin', 'ffmpeg'),
        'ffmpeg'
    ];
    
    for (const ffmpegPath of possiblePaths) {
        try {
            if (ffmpegPath === 'ffmpeg' || fs.existsSync(ffmpegPath)) {
                console.log(` FFmpeg found: ${ffmpegPath}`);
                return ffmpegPath;
            }
        } catch (error) {
            continue;
        }
    }
    
    console.log(' FFmpeg not found');
    return null;
}

// 動画ファイルのパス解決
function resolveVideoPath(videoName) {
    const paths = [
        videoName,
        path.join(moviesDir, videoName),
        path.join(workspaceRoot, videoName)
    ];
    
    for (const videoPath of paths) {
        if (fs.existsSync(videoPath)) {
            console.log(` Video found: ${videoPath}`);
            return path.resolve(videoPath);
        }
    }
    
    console.error(` Video file not found: ${videoName}`);
    return null;
}

// テレメトリストリームの抽出
async function extractTelemetryStream(videoPath, ffmpegPath, outputBaseName) {
    console.log(`\n  Extracting telemetry stream from video...`);
    
    const binFile = path.join(outputDir, `${outputBaseName}_telemetry.bin`);
    
    // 既存ファイルを削除
    if (fs.existsSync(binFile)) {
        fs.unlinkSync(binFile);
    }
    
    // Stream 3を抽出（GoProの標準テレメトリストリーム）
    return new Promise((resolve, reject) => {
        const args = [
            '-y',
            '-i', videoPath,
            '-codec', 'copy',
            '-map', '0:3',
            '-f', 'rawvideo',
            binFile
        ];
        
        console.log(` Running: ffmpeg ${args.slice(2).join(' ')}`);
        
        const ffmpeg = spawn(ffmpegPath, args, { stdio: 'pipe' });
        
        ffmpeg.on('close', (code) => {
            if (code === 0 && fs.existsSync(binFile)) {
                const stats = fs.statSync(binFile);
                if (stats.size > 1000) { // 最低1KB以上
                    console.log(` Telemetry extracted: ${(stats.size / 1024).toFixed(2)} KB`);
                    resolve(binFile);
                } else {
                    console.log(`  Stream 3 too small, trying alternative streams...`);
                    // Stream 2や4を試行
                    tryAlternativeStreams(videoPath, ffmpegPath, outputBaseName)
                        .then(resolve)
                        .catch(reject);
                }
            } else {
                console.log(` FFmpeg failed with code: ${code}`);
                reject(new Error('Telemetry extraction failed'));
            }
        });
        
        ffmpeg.on('error', (error) => {
            console.log(` FFmpeg error: ${error.message}`);
            reject(error);
        });
    });
}

// 代替ストリームの試行
async function tryAlternativeStreams(videoPath, ffmpegPath, outputBaseName) {
    console.log(` Trying alternative streams...`);
    
    const streams = [2, 4, 5];
    
    for (const streamIndex of streams) {
        console.log(` Trying stream ${streamIndex}...`);
        
        const binFile = path.join(outputDir, `${outputBaseName}_stream_${streamIndex}.bin`);
        
        const success = await new Promise((resolve) => {
            const args = ['-y', '-i', videoPath, '-codec', 'copy', '-map', `0:${streamIndex}`, '-f', 'rawvideo', binFile];
            const ffmpeg = spawn(ffmpegPath, args, { stdio: 'pipe' });
            
            ffmpeg.on('close', (code) => {
                if (code === 0 && fs.existsSync(binFile) && fs.statSync(binFile).size > 1000) {
                    const size = fs.statSync(binFile).size;
                    console.log(` Stream ${streamIndex}: ${(size / 1024).toFixed(2)} KB`);
                    resolve(binFile);
                } else {
                    if (fs.existsSync(binFile)) fs.unlinkSync(binFile);
                    resolve(null);
                }
            });
            
            ffmpeg.on('error', () => resolve(null));
        });
        
        if (success) {
            return success;
        }
    }
    
    throw new Error('No suitable telemetry stream found');
}

// GoPro Max専用パーサークラス
class GoProMaxParser {
    constructor(binaryData) {
        this.data = binaryData;
        this.extractedData = {
            GPS5: [],
            ACCL: [],
            GYRO: [],
            CORI: []
        };
    }
    
    // GPS5データの検索と解析
    findAndParseGPS5() {
        console.log(`\n🔍 Searching for GPS5 data...`);
        
        const gps5Positions = [];
        let searchPos = 0;
        
        while (searchPos < this.data.length - 4) {
            const index = this.data.indexOf(Buffer.from('GPS5'), searchPos);
            if (index === -1) break;
            gps5Positions.push(index);
            searchPos = index + 1;
        }
        
        console.log(` Found GPS5 at ${gps5Positions.length} positions`);
        
        gps5Positions.forEach((pos, i) => {
            this.parseGPS5Block(pos, i + 1);
        });
        
        return gps5Positions.length > 0;
    }
    
    // GPS5ブロックの解析
    parseGPS5Block(startPos, blockNum) {
        console.log(` Processing GPS5 block ${blockNum} at position ${startPos}`);
        
        // GPS5タグの後のデータ構造を解析
        let dataStart = startPos + 8; // GPS5 + 基本ヘッダー
        
        // サンプル数を推定（GoProの一般的なパターン）
        const maxSamples = Math.min(20, Math.floor((this.data.length - dataStart) / 20));
        
        const coordinates = [];
        
        for (let i = 0; i < maxSamples; i++) {
            const offset = dataStart + (i * 20);
            
            if (offset + 20 > this.data.length) break;
            
            try {
                // リトルエンディアンで解析（GoProの標準）
                const lat = this.data.readInt32LE(offset) / 10000000.0;
                const lon = this.data.readInt32LE(offset + 4) / 10000000.0;
                const alt = this.data.readInt32LE(offset + 8) / 1000.0;
                const speed2d = this.data.readInt32LE(offset + 12) / 1000.0;
                const speed3d = this.data.readInt32LE(offset + 16) / 1000.0;
                
                // 座標の妥当性チェック
                if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180 && lat !== 0 && lon !== 0) {
                    coordinates.push({
                        latitude: lat,
                        longitude: lon,
                        altitude: alt,
                        speed_2d: Math.abs(speed2d),
                        speed_3d: Math.abs(speed3d)
                    });
                }
            } catch (error) {
                break;
            }
        }
        
        if (coordinates.length > 0) {
            this.extractedData.GPS5.push(...coordinates);
            console.log(` Extracted ${coordinates.length} GPS coordinates`);
            
            // 最初の座標を表示
            const first = coordinates[0];
            console.log(`   First coordinate: ${first.latitude.toFixed(6)}, ${first.longitude.toFixed(6)}, ${first.altitude.toFixed(1)}m`);
        }
    }
    
    // センサーデータの検索と解析
    findAndParseSensorData(tagName) {
        console.log(`\n Searching for ${tagName} data...`);
        
        const positions = [];
        let searchPos = 0;
        
        while (searchPos < this.data.length - 4) {
            const index = this.data.indexOf(Buffer.from(tagName), searchPos);
            if (index === -1) break;
            positions.push(index);
            searchPos = index + 1;
        }
        
        console.log(` Found ${tagName} at ${positions.length} positions`);
        
        positions.forEach((pos, i) => {
            this.parseSensorBlock(pos, tagName, i + 1);
        });
        
        return positions.length > 0;
    }
    
    // センサーブロックの解析
    parseSensorBlock(startPos, tagName, blockNum) {
        console.log(` Processing ${tagName} block ${blockNum} at position ${startPos}`);
        
        let dataStart = startPos + 12; // タグ + ヘッダー
        const sampleSize = tagName === 'CORI' ? 8 : 6;
        const maxSamples = Math.min(100, Math.floor((this.data.length - dataStart) / sampleSize));
        
        const samples = [];
        
        for (let i = 0; i < maxSamples; i++) {
            const offset = dataStart + (i * sampleSize);
            
            if (offset + sampleSize > this.data.length) break;
            
            try {
                if (tagName === 'ACCL' || tagName === 'GYRO') {
                    // 3軸センサーデータ
                    const x = this.data.readInt16LE(offset) / 1000.0;
                    const y = this.data.readInt16LE(offset + 2) / 1000.0;
                    const z = this.data.readInt16LE(offset + 4) / 1000.0;
                    
                    samples.push({ x, y, z });
                } else if (tagName === 'CORI') {
                    // クォータニオン
                    const w = this.data.readInt16LE(offset) / 32767.0;
                    const x = this.data.readInt16LE(offset + 2) / 32767.0;
                    const y = this.data.readInt16LE(offset + 4) / 32767.0;
                    const z = this.data.readInt16LE(offset + 6) / 32767.0;
                    
                    samples.push({ w, x, y, z });
                }
            } catch (error) {
                break;
            }
        }
        
        if (samples.length > 0) {
            this.extractedData[tagName].push(...samples);
            console.log(` Extracted ${samples.length} ${tagName} samples`);
        }
    }
    
    // メイン解析処理
    parse() {
        console.log(`\n Starting telemetry data parsing...`);
        console.log(` Binary data size: ${(this.data.length / 1024).toFixed(2)} KB`);
        
        // 各データタイプを解析
        this.findAndParseGPS5();
        this.findAndParseSensorData('ACCL');
        this.findAndParseSensorData('GYRO');
        this.findAndParseSensorData('CORI');
        
        // 結果サマリー
        console.log(`\n Parsing Results:`);
        console.log(` GPS coordinates: ${this.extractedData.GPS5.length}`);
        console.log(` Accelerometer samples: ${this.extractedData.ACCL.length}`);
        console.log(` Gyroscope samples: ${this.extractedData.GYRO.length}`);
        console.log(` Orientation samples: ${this.extractedData.CORI.length}`);
        
        return this.extractedData;
    }
}

// CSVファイルの生成
function generateCSV(extractedData, outputBaseName) {
    console.log(`\n Generating CSV file...`);
    
    const csvFile = path.join(outputDir, `${outputBaseName}_telemetry.csv`);
    
    // 最大サンプル数を決定
    const maxSamples = Math.max(
        extractedData.GPS5.length,
        extractedData.ACCL.length,
        extractedData.GYRO.length,
        extractedData.CORI.length,
        1
    );
    
    console.log(` Generating ${maxSamples} data rows`);
    
    // CSVヘッダー
    const headers = ['index', 'timestamp'];
    
    if (extractedData.GPS5.length > 0) {
        headers.push('latitude', 'longitude', 'altitude', 'speed_2d', 'speed_3d');
    }
    
    if (extractedData.ACCL.length > 0) {
        headers.push('accel_x', 'accel_y', 'accel_z');
    }
    
    if (extractedData.GYRO.length > 0) {
        headers.push('gyro_x', 'gyro_y', 'gyro_z');
    }
    
    if (extractedData.CORI.length > 0) {
        headers.push('orientation_w', 'orientation_x', 'orientation_y', 'orientation_z');
    }
    
    const csvLines = [headers.join(',')];
    
    // データ行の生成
    for (let i = 0; i < maxSamples; i++) {
        const row = [i.toString(), (i * 0.033333).toFixed(6)]; // 30fps想定
        
        // GPS5データ
        if (extractedData.GPS5.length > 0) {
            const gps = extractedData.GPS5[i] || {};
            row.push(
                (gps.latitude || 0).toFixed(7),
                (gps.longitude || 0).toFixed(7),
                (gps.altitude || 0).toFixed(3),
                (gps.speed_2d || 0).toFixed(3),
                (gps.speed_3d || 0).toFixed(3)
            );
        }
        
        // 加速度データ
        if (extractedData.ACCL.length > 0) {
            const accl = extractedData.ACCL[i] || {};
            row.push(
                (accl.x || 0).toFixed(6),
                (accl.y || 0).toFixed(6),
                (accl.z || 0).toFixed(6)
            );
        }
        
        // ジャイロデータ
        if (extractedData.GYRO.length > 0) {
            const gyro = extractedData.GYRO[i] || {};
            row.push(
                (gyro.x || 0).toFixed(6),
                (gyro.y || 0).toFixed(6),
                (gyro.z || 0).toFixed(6)
            );
        }
        
        // オリエンテーションデータ
        if (extractedData.CORI.length > 0) {
            const cori = extractedData.CORI[i] || {};
            row.push(
                (cori.w || 1).toFixed(6),
                (cori.x || 0).toFixed(6),
                (cori.y || 0).toFixed(6),
                (cori.z || 0).toFixed(6)
            );
        }
        
        csvLines.push(row.join(','));
    }
    
    // ファイルに書き込み
    fs.writeFileSync(csvFile, csvLines.join('\n'));
    
    const fileSize = fs.statSync(csvFile).size;
    console.log(` CSV file created: ${path.basename(csvFile)}`);
    console.log(` File size: ${(fileSize / 1024).toFixed(2)} KB`);
    console.log(` Rows: ${csvLines.length - 1} (excluding header)`);
    console.log(` Columns: ${headers.length}`);
    
    return {
        csvFile,
        rows: csvLines.length - 1,
        columns: headers.length,
        headers
    };
}

// GPS データの分析
function analyzeGPSData(extractedData) {
    if (extractedData.GPS5.length === 0) {
        console.log('\n  No GPS data found');
        return;
    }
    
    console.log(`\n  GPS Data Analysis:`);
    
    const validGPS = extractedData.GPS5.filter(p => p.latitude !== 0 && p.longitude !== 0);
    
    if (validGPS.length > 0) {
        const lats = validGPS.map(p => p.latitude);
        const lons = validGPS.map(p => p.longitude);
        const alts = validGPS.map(p => p.altitude);
        
        console.log(` Valid GPS points: ${validGPS.length} / ${extractedData.GPS5.length}`);
        console.log(` Latitude range: ${Math.min(...lats).toFixed(6)} to ${Math.max(...lats).toFixed(6)}`);
        console.log(` Longitude range: ${Math.min(...lons).toFixed(6)} to ${Math.max(...lons).toFixed(6)}`);
        console.log(`  Altitude range: ${Math.min(...alts).toFixed(1)}m to ${Math.max(...alts).toFixed(1)}m`);
        
        const centerLat = lats.reduce((a, b) => a + b, 0) / lats.length;
        const centerLon = lons.reduce((a, b) => a + b, 0) / lons.length;
        const avgAlt = alts.reduce((a, b) => a + b, 0) / alts.length;
        
        console.log(` Center point: ${centerLat.toFixed(6)}, ${centerLon.toFixed(6)}`);
        console.log(` Average altitude: ${avgAlt.toFixed(1)}m`);
    }
}

// メイン統合処理
async function processVideo(videoName) {
    const startTime = Date.now();
    
    try {
        console.log(`\n Processing GoPro .360 video: ${videoName}`);
        console.log('='.repeat(50));
        
        // 1. 前提条件の確認
        const videoPath = resolveVideoPath(videoName);
        if (!videoPath) {
            throw new Error(`Video file not found: ${videoName}`);
        }
        
        const ffmpegPath = findFFmpeg();
        if (!ffmpegPath) {
            throw new Error('FFmpeg not found');
        }
        
        // 2. テレメトリストリームの抽出
        const outputBaseName = path.parse(videoName).name;
        const binFile = await extractTelemetryStream(videoPath, ffmpegPath, outputBaseName);
        
        // 3. バイナリデータの読み込み
        const binaryData = fs.readFileSync(binFile);
        console.log(` Binary data loaded: ${(binaryData.length / 1024).toFixed(2)} KB`);
        
        // 4. テレメトリデータの解析
        const parser = new GoProMaxParser(binaryData);
        const extractedData = parser.parse();
        
        // 5. GPS データの分析
        analyzeGPSData(extractedData);
        
        // 6. CSVファイルの生成
        const csvResult = generateCSV(extractedData, outputBaseName);
        
        // 7. 一時ファイルのクリーンアップ
        if (fs.existsSync(binFile)) {
            fs.unlinkSync(binFile);
            console.log(`  Temporary .bin file cleaned up`);
        }
        
        const totalTime = Date.now() - startTime;
        
        console.log('\n Processing completed successfully!');
        console.log('=====================================');
        console.log(`  Total processing time: ${(totalTime / 1000).toFixed(2)}s`);
        console.log(` Source video: ${videoName}`);
        console.log(` CSV output: ${path.basename(csvResult.csvFile)}`);
        console.log(` Data points: ${csvResult.rows}`);
        console.log(` Columns: ${csvResult.columns}`);
        
        return {
            success: true,
            csvFile: csvResult.csvFile,
            videoPath,
            extractedData,
            processingTime: totalTime
        };
        
    } catch (error) {
        console.error(`\n Processing failed: ${error.message}`);
        return {
            success: false,
            error: error.message
        };
    }
}

// メイン実行部
async function main() {
    const videoName = process.argv[2];
    
    if (!videoName) {
        console.log(' Usage: node gopro_360_to_csv.js <video_file>');
        console.log('');
        console.log('Examples:');
        console.log('  node gopro_360_to_csv.js GS010678.360');
        console.log('  node gopro_360_to_csv.js GOPR1234.MP4');
        console.log('');
        console.log(' This tool directly converts GoPro .360 videos to CSV telemetry data');
        console.log(' Output: Complete CSV with GPS, accelerometer, gyroscope, and orientation data');
        console.log(' Automatically cleans up temporary files');
        console.log('');
        console.log(' Prerequisites:');
        console.log('  • FFmpeg installed in include/ffmpeg/ or system PATH');
        console.log('  • GoPro video with telemetry data (Hero5+, Max, etc.)');
        process.exit(1);
    }
    
    const result = await processVideo(videoName);
    
    if (result.success) {
        console.log('\n Next steps:');
        console.log(`   • View data: Open ${path.basename(result.csvFile)} in Excel/LibreOffice`);
        console.log('   • Create maps: Import GPS coordinates to mapping software');
        console.log(`   • Process images: python3 process_telemetry_csv.py ${videoName} ${path.basename(result.csvFile)}`);
        console.log('   • Analyze sensors: Plot accelerometer/gyroscope data for motion analysis');
        
        process.exit(0);
    } else {
        console.log('\n Troubleshooting:');
        console.log('  • Ensure the video is from a GoPro camera with telemetry support');
        console.log('  • Check that GPS was enabled during recording');
        console.log('  • Verify FFmpeg is properly installed');
        console.log('  • Try with a different GoPro video file');
        
        process.exit(1);
    }
}

main();
