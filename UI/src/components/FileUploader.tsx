import { Upload } from "lucide-react";
import { motion } from "motion/react";

interface FileUploaderProps {
  onFileUpload: (file: File) => void;
}

export function FileUploader({ onFileUpload }: FileUploaderProps) {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileUpload(file);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-md"
    >
      <label
        htmlFor="file-upload"
        className="flex flex-col items-center justify-center w-full h-64 border-2 border-cyan-500/30 border-dashed rounded-2xl cursor-pointer bg-cyan-950/20 backdrop-blur-sm hover:bg-cyan-900/30 transition-all duration-300 hover:border-cyan-400/50"
      >
        <div className="flex flex-col items-center justify-center pt-5 pb-6">
          <Upload className="w-12 h-12 mb-4 text-cyan-300" />
          <p className="mb-2 text-cyan-100">
            <span>Click to upload</span> or drag and drop
          </p>
          <p className="text-cyan-300/60">JSON file</p>
        </div>
        <input
          id="file-upload"
          type="file"
          className="hidden"
          accept=".json"
          onChange={handleFileChange}
        />
      </label>
    </motion.div>
  );
}
