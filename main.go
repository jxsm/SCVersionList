package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// FileDetail 表示每个文件的详细信息
type FileDetail struct {
	SubVersion string `json:"sub_version"`
	Size       int64  `json:"size"`
	Path       string `json:"path"`
	FileFormat string `json:"file_format"`
	Illustrate string `json:"illustrate"`
	Sha256     string `json:"sha256"`
}

// Manifest 清单的整体结构
type Manifest struct {
	API      map[string][]FileDetail `json:"api"`
	NET      map[string][]FileDetail `json:"net"`
	Original map[string][]FileDetail `json:"original"`
}

func main() {
	// 根目录（请根据实际情况修改）
	rootDir := `./`
	// 输出清单文件路径
	outputPath := "manifest.json"

	// 初始化清单结构
	manifest := Manifest{
		API: make(map[string][]FileDetail),
		NET: make(map[string][]FileDetail),
	}

	// 处理API插件版目录
	apiDir := filepath.Join(rootDir, "API")
	if err := processDir(apiDir, "API插件版", manifest.API, "API"); err != nil {
		fmt.Printf("处理API目录出错: %v\n", err)
	}

	// 处理NET联机版目录
	netDir := filepath.Join(rootDir, "NET")
	if err := processDir(netDir, "NET 联机版", manifest.NET, "NET"); err != nil {
		fmt.Printf("处理NET目录出错: %v\n", err)
	}

	// 生成带缩进的JSON
	jsonData, err := json.MarshalIndent(manifest, "", "    ")
	if err != nil {
		fmt.Printf("JSON序列化失败: %v\n", err)
		return
	}

	// 写入文件
	if err := os.WriteFile(outputPath, jsonData, 0644); err != nil {
		fmt.Printf("写入文件失败: %v\n", err)
		return
	}

	fmt.Printf("清单文件已生成: %s\n", outputPath)
}

// 处理目录下的文件并按版本分组
func processDir(dirPath, relativeRoot string, versionMap map[string][]FileDetail, typePrefix string) error {
	entries, err := os.ReadDir(dirPath)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		if entry.IsDir() {
			continue // 跳过子目录
		}

		fileName := entry.Name()
		fullPath := filepath.Join(dirPath, fileName)

		// 获取文件信息（大小）
		fileInfo, err := entry.Info()
		if err != nil {
			fmt.Printf("获取文件信息失败(%s): %v\n", fileName, err)
			continue
		}

		// 计算SHA256
		sha256Str, err := getFileSHA256(fullPath)
		if err != nil {
			fmt.Printf("计算SHA256失败(%s): %v\n", fileName, err)
			sha256Str = ""
		}

		// 解析版本和子版本
		mainVersion, subVersion := parseVersionInfo(fileName, typePrefix)
		if mainVersion == "" {
			fmt.Printf("无法解析版本信息: %s\n", fileName)
			continue
		}

		// 解析文件格式
		ext := filepath.Ext(fileName)
		fileFormat := strings.TrimPrefix(ext, ".")

		// 构建相对路径
		relativePath := filepath.Join(relativeRoot, fileName)

		// 构建文件详情
		fileDetail := FileDetail{
			SubVersion: subVersion,
			Size:       fileInfo.Size(),
			Path:       relativePath,
			FileFormat: fileFormat,
			Illustrate: "",
			Sha256:     sha256Str,
		}

		// 添加到对应版本组
		versionMap[mainVersion] = append(versionMap[mainVersion], fileDetail)
	}

	return nil
}

// 解析文件名中的主版本和子版本
func parseVersionInfo(fileName, typePrefix string) (mainVersion, subVersion string) {
	// 移除文件扩展名
	nameWithoutExt := strings.TrimSuffix(fileName, filepath.Ext(fileName))

	// 分割主版本和子版本（根据类型前缀）
	sep := " " + typePrefix + " "
	parts := strings.SplitN(nameWithoutExt, sep, 2)
	if len(parts) == 2 {
		return parts[0], typePrefix + " " + parts[1]
	}

	// 兼容带数字后缀的前缀（如API0）
	sep = " " + typePrefix
	for i := 0; i <= 9; i++ {
		testSep := sep + fmt.Sprintf("%d ", i)
		if strings.Contains(nameWithoutExt, testSep) {
			parts := strings.SplitN(nameWithoutExt, testSep, 2)
			if len(parts) == 2 {
				return parts[0], typePrefix + fmt.Sprintf("%d ", i) + parts[1]
			}
		}
	}

	return "", ""
}

// 计算文件的SHA256哈希
func getFileSHA256(filePath string) (string, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer file.Close()

	hash := sha256.New()
	if _, err := io.Copy(hash, file); err != nil {
		return "", err
	}

	return hex.EncodeToString(hash.Sum(nil)), nil
}
