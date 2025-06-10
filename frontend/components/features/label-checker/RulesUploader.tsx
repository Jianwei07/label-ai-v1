"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { FileText, CheckCircle2 } from "lucide-react";

interface RulesUploaderProps {
  onFileSelect: (file: File) => void;
  currentFile: File | null;
}

export function RulesUploader({
  onFileSelect,
  currentFile,
}: RulesUploaderProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles && acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
      "application/json": [".json"],
      "application/x-yaml": [".yaml", ".yml"],
    },
    multiple: false,
  });

  return (
    <div
      {...getRootProps()}
      className={`relative p-6 border-2 border-dashed rounded-lg text-center cursor-pointer transition-colors
        ${
          isDragActive
            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
            : "border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500"
        }`}
    >
      <input {...getInputProps()} />
      {currentFile ? (
        <div className="flex items-center justify-center gap-2 text-green-600 dark:text-green-400">
          <CheckCircle2 className="w-5 h-5" />
          <p className="font-medium">
            {currentFile.name} selected. Click or drop to replace.
          </p>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center space-y-2 text-gray-600 dark:text-gray-300">
          <FileText className="w-12 h-12 text-gray-400 dark:text-gray-500" />
          {isDragActive ? (
            <p>Drop the rules file here ...</p>
          ) : (
            <p>Drag & drop your rules file here, or click to select</p>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400">
            DOCX, JSON, or YAML
          </p>
        </div>
      )}
    </div>
  );
}
