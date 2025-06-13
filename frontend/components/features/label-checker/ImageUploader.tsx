"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, CheckCircle2 } from "lucide-react";
import Image from "next/image";

interface ImageUploaderProps {
  onFileSelect: (file: File) => void;
  onFileRemove: () => void; // <-- Add this line
  currentImageUrl: string | null;
}

export function ImageUploader({
  onFileSelect,
  currentImageUrl,
}: ImageUploaderProps) {
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
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
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
      {currentImageUrl ? (
        <div className="space-y-2">
          <div className="w-24 h-24 mx-auto relative rounded-md overflow-hidden">
            <Image
              src={currentImageUrl}
              alt="Preview"
              fill
              className="object-cover"
            />
          </div>
          <div className="flex items-center justify-center gap-2 text-green-600 dark:text-green-400">
            <CheckCircle2 className="w-5 h-5" />
            <p className="font-medium">
              Image selected. Click or drop to replace.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center space-y-2 text-gray-600 dark:text-gray-300">
          <UploadCloud className="w-12 h-12 text-gray-400 dark:text-gray-500" />
          {isDragActive ? (
            <p>Drop the image here ...</p>
          ) : (
            <p>Drag & drop your label image here, or click to select</p>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400">PNG or JPG</p>
        </div>
      )}
    </div>
  );
}
