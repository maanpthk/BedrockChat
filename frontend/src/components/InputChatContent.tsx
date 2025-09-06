import React, {
  forwardRef,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import ButtonSend from './ButtonSend';
import Textarea from './Textarea';
import { AttachmentType, S3AttachmentType } from '../hooks/useChat';
import Button from './Button';
import {
  PiArrowsCounterClockwise,
  PiX,
  PiArrowFatLineRight,
} from 'react-icons/pi';
import { LuFilePlus2 } from 'react-icons/lu';
import { useTranslation } from 'react-i18next';
import ButtonIcon from './ButtonIcon';
import useModel from '../hooks/useModel';
import { produce } from 'immer';
import { twMerge } from 'tailwind-merge';
import { create } from 'zustand';
import ButtonFileChoose from './ButtonFileChoose';
import ButtonReasoning from './ButtonReasoning';
import { BaseProps } from '../@types/common';
import ModalDialog from './ModalDialog';
import UploadedAttachedFile from './UploadedAttachedFile';
import useSnackbar from '../hooks/useSnackbar';
import {
  MAX_FILE_SIZE_BYTES,
  MAX_FILE_SIZE_MB,
  SUPPORTED_FILE_EXTENSIONS,
  MAX_ATTACHED_FILES,
  MAX_SUPPORTED_FILE_SIZE_BYTES,
  MAX_SUPPORTED_FILE_SIZE_MB,
  BEDROCK_MAX_FILE_SIZE_BYTES,
  BEDROCK_MAX_FILE_SIZE_MB,
} from '../constants/supportedAttachedFiles';

type Props = BaseProps & {
  disabledSend?: boolean;
  disabledRegenerate?: boolean;
  disabledContinue?: boolean;
  disabled?: boolean;
  placeholder?: string;
  dndMode?: boolean;
  canRegenerate: boolean;
  canContinue: boolean;
  isLoading: boolean;
  isNewChat?: boolean;
  conversationId?: string;
  onSend: (
    content: string,
    enableReasoning: boolean,
    base64EncodedImages?: string[],
    attachments?: AttachmentType[],
    s3Attachments?: S3AttachmentType[]
  ) => void;
  onRegenerate: (enableReasoning: boolean) => void;
  continueGenerate: () => void;
  supportReasoning: boolean;
  reasoningEnabled: boolean;
  onChangeReasoning: (enabled: boolean) => void;
};
// Image size
// Ref: https://docs.anthropic.com/en/docs/build-with-claude/vision#evaluate-image-size
const MAX_IMAGE_WIDTH = 1568;
const MAX_IMAGE_HEIGHT = 1568;
// All files now go to S3 to avoid Lambda response size limits

const useInputChatContentState = create<{
  base64EncodedImages: string[];
  pushBase64EncodedImage: (encodedImage: string) => void;
  removeBase64EncodedImage: (index: number) => void;
  clearBase64EncodedImages: () => void;
  attachedFiles: {
    name: string;
    type: string;
    size: number;
    content: string;
  }[];
  pushTextFile: (file: {
    name: string;
    type: string;
    size: number;
    content: string;
  }) => void;
  removeTextFile: (index: number) => void;
  clearAttachedFiles: () => void;
  s3AttachedFiles: {
    name: string;
    type: string;
    size: number;
    s3Key: string;
  }[];
  pushS3File: (file: {
    name: string;
    type: string;
    size: number;
    s3Key: string;
  }) => void;
  removeS3File: (index: number) => void;
  clearS3AttachedFiles: () => void;
  previewImageUrl: string | null;
  setPreviewImageUrl: (url: string | null) => void;
  isOpenPreviewImage: boolean;
  setIsOpenPreviewImage: (isOpen: boolean) => void;

}>((set, get) => ({
  base64EncodedImages: [],
  pushBase64EncodedImage: (encodedImage) => {
    set({
      base64EncodedImages: produce(get().base64EncodedImages, (draft) => {
        draft.push(encodedImage);
      }),
    });
  },
  removeBase64EncodedImage: (index) => {
    set({
      base64EncodedImages: produce(get().base64EncodedImages, (draft) => {
        draft.splice(index, 1);
      }),
    });
  },
  clearBase64EncodedImages: () => {
    set({
      base64EncodedImages: [],
    });
  },
  previewImageUrl: null,
  setPreviewImageUrl: (url) => {
    set({ previewImageUrl: url });
  },
  isOpenPreviewImage: false,
  setIsOpenPreviewImage: (isOpen) => {
    set({ isOpenPreviewImage: isOpen });
  },
  attachedFiles: [],
  pushTextFile: (file) => {
    set({
      attachedFiles: produce(get().attachedFiles, (draft) => {
        draft.push(file);
      }),
    });
  },
  removeTextFile: (index) => {
    set({
      attachedFiles: produce(get().attachedFiles, (draft) => {
        draft.splice(index, 1);
      }),
    });
  },
  clearAttachedFiles: () => {
    set({
      attachedFiles: [],
    });
  },
  s3AttachedFiles: [],
  pushS3File: (file) => {
    set({
      s3AttachedFiles: produce(get().s3AttachedFiles, (draft) => {
        draft.push(file);
      }),
    });
  },
  removeS3File: (index) => {
    set({
      s3AttachedFiles: produce(get().s3AttachedFiles, (draft) => {
        draft.splice(index, 1);
      }),
    });
  },
  clearS3AttachedFiles: () => {
    set({
      s3AttachedFiles: [],
    });
  },

}));

const InputChatContent = forwardRef<HTMLElement, Props>(
  (props, focusInputRef) => {
    const { t } = useTranslation();
    const {
      disabledImageUpload,
      model,
      acceptMediaType,
      forceReasoningEnabled,
    } = useModel();

    const extendedAcceptMediaType = useMemo(() => {
      return [...acceptMediaType, ...SUPPORTED_FILE_EXTENSIONS];
    }, [acceptMediaType]);

    const [content, setContent] = useState('');
    const { reasoningEnabled, onChangeReasoning } = props;

    const {
      base64EncodedImages,
      pushBase64EncodedImage,
      removeBase64EncodedImage,
      clearBase64EncodedImages,
      previewImageUrl,
      setPreviewImageUrl,
      isOpenPreviewImage,
      setIsOpenPreviewImage,
      attachedFiles,
      pushTextFile,
      removeTextFile,
      clearAttachedFiles,
      s3AttachedFiles,
      pushS3File,
      removeS3File,
      clearS3AttachedFiles,
    } = useInputChatContentState();

    useEffect(() => {
      clearBase64EncodedImages();
      clearAttachedFiles();
      clearS3AttachedFiles();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const { open } = useSnackbar();

    const disabledSend = useMemo(() => {
      return content === '' || props.disabledSend;
    }, [content, props.disabledSend]);

    const inputRef = useRef<HTMLDivElement>(null);

    const sendContent = useCallback(() => {
      const attachments = attachedFiles.map((file) => ({
        fileName: file.name,
        fileType: file.type,
        extractedContent: file.content,
      }));

      const s3Attachments = s3AttachedFiles.map((file) => ({
        fileName: file.name,
        fileType: file.type,
        s3Key: file.s3Key,
        fileSize: file.size,
      }));

      props.onSend(
        content,
        props.reasoningEnabled,
        !disabledImageUpload && base64EncodedImages.length > 0
          ? base64EncodedImages
          : undefined,
        attachments.length > 0 ? attachments : undefined,
        s3Attachments.length > 0 ? s3Attachments : undefined
      );
      setContent('');
      clearBase64EncodedImages();
      clearAttachedFiles();
      clearS3AttachedFiles();
    }, [
      base64EncodedImages,
      attachedFiles,
      s3AttachedFiles,
      clearBase64EncodedImages,
      clearAttachedFiles,
      clearS3AttachedFiles,
      content,
      disabledImageUpload,
      props,
    ]);

    const encodeAndPushImage = useCallback(
      (imageFile: File) => {
        const reader = new FileReader();
        reader.readAsArrayBuffer(imageFile);
        reader.onload = () => {
          if (!reader.result) {
            return;
          }

          const img = new Image();
          img.src = URL.createObjectURL(new Blob([reader.result]));
          img.onload = async () => {
            const width = img.naturalWidth;
            const height = img.naturalHeight;

            // determine image size
            const aspectRatio = width / height;
            let newWidth;
            let newHeight;
            if (aspectRatio > 1) {
              newWidth = width > MAX_IMAGE_WIDTH ? MAX_IMAGE_WIDTH : width;
              newHeight =
                width > MAX_IMAGE_WIDTH
                  ? MAX_IMAGE_WIDTH / aspectRatio
                  : height;
            } else {
              newHeight = height > MAX_IMAGE_HEIGHT ? MAX_IMAGE_HEIGHT : height;
              newWidth =
                height > MAX_IMAGE_HEIGHT
                  ? MAX_IMAGE_HEIGHT * aspectRatio
                  : width;
            }

            // resize image using canvas
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = newWidth;
            canvas.height = newHeight;
            ctx?.drawImage(img, 0, 0, newWidth, newHeight);

            const resizedImageData = canvas.toDataURL('image/png');

            // Images still use base64 for now (could be moved to S3 later if needed)
            pushBase64EncodedImage(resizedImageData);
          };
        };
      },
      [
        pushBase64EncodedImage,
        open,
        t,
      ]
    );

    const handleAttachedFileRead = useCallback(
      async (file: File) => {
        // Check maximum supported file size
        if (file.size > MAX_SUPPORTED_FILE_SIZE_BYTES) {
          open(
            t('error.attachment.fileSizeExceeded', {
              maxSize: `${MAX_SUPPORTED_FILE_SIZE_MB} MB`,
            })
          );
          return;
        }

        // All files now go to S3 to avoid Lambda response size limits
        
        // Check if PDF should be split
        const shouldSplitPDF = file.type === 'application/pdf' && file.size > BEDROCK_MAX_FILE_SIZE_BYTES;

        // Always use S3 storage
        await handleLargeFileUpload(file, shouldSplitPDF);
      },
      [handleLargeFileUpload, open, t]
    );



    const handleLargeFileUpload = useCallback(
      async (file: File, shouldSplit: boolean) => {
        try {
          // Import S3 utilities dynamically
          const { 
            getDocumentUploadUrl, 
            uploadFileToS3, 
            splitPDF 
          } = await import('../utils/s3Documents');

          if (shouldSplit) {
            // Upload original PDF first
            const uploadResponse = await getDocumentUploadUrl(props.conversationId || 'temp', {
              filename: file.name,
              content_type: file.type,
              file_size: file.size,
            });

            await uploadFileToS3(uploadResponse.uploadUrl, file);

            // Split the PDF
            const splitResponse = await splitPDF(props.conversationId || 'temp', {
              s3_key: uploadResponse.s3Key,
              max_size_mb: BEDROCK_MAX_FILE_SIZE_MB,
            });

            // Add each chunk as S3 attachment (no base64 conversion needed)
            splitResponse.chunks.forEach((chunk) => {
              pushS3File({
                name: chunk.fileName,
                type: file.type,
                size: chunk.sizeBytes,
                s3Key: chunk.s3Key,
              });
            });

            open(
              t('info.pdfSplit', {
                chunks: splitResponse.totalChunks,
                defaultValue: `PDF split into ${splitResponse.totalChunks} parts`,
              })
            );
          } else {
            // Upload large file to S3
            // Note: We'll need the conversation ID from props or context
            const uploadResponse = await getDocumentUploadUrl(props.conversationId || 'temp', {
              filename: file.name,
              content_type: file.type,
              file_size: file.size,
            });

            await uploadFileToS3(uploadResponse.uploadUrl, file);

            pushS3File({
              name: file.name,
              type: file.type,
              size: file.size,
              s3Key: uploadResponse.s3Key,
            });
          }
        } catch (error) {
          console.error('Error handling large file:', error);
          open(
            t('error.fileUploadFailed', {
              defaultValue: 'Failed to upload file',
            })
          );
        }
      },
      [pushS3File, open, t, props.conversationId]
    );

    useEffect(() => {
      const currentElem = inputRef?.current;
      const keypressListener = (e: DocumentEventMap['keypress']) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();

          if (!disabledSend) {
            sendContent();
          }
        }
      };
      currentElem?.addEventListener('keypress', keypressListener);

      const pasteListener = (e: DocumentEventMap['paste']) => {
        const clipboardItems = e.clipboardData?.items;
        if (!clipboardItems || clipboardItems.length === 0) {
          return;
        }

        for (let i = 0; i < clipboardItems.length; i++) {
          if (model?.supportMediaType.includes(clipboardItems[i].type)) {
            const pastedFile = clipboardItems[i].getAsFile();
            if (pastedFile) {
              encodeAndPushImage(pastedFile);
              e.preventDefault();
            }
          }
        }
      };
      currentElem?.addEventListener('paste', pasteListener);

      return () => {
        currentElem?.removeEventListener('keypress', keypressListener);
        currentElem?.removeEventListener('paste', pasteListener);
      };
    });

    const onChangeFile = useCallback(
      (fileList: FileList) => {
        // Check if the total number of attached files exceeds the limit
        const currentAttachedFiles =
          useInputChatContentState.getState().attachedFiles;
        const currentS3AttachedFiles =
          useInputChatContentState.getState().s3AttachedFiles;
        const currentAttachedFilesCount = currentAttachedFiles.filter((file) =>
          SUPPORTED_FILE_EXTENSIONS.some((extension) =>
            file.name.endsWith(extension)
          )
        ).length + currentS3AttachedFiles.length;

        let newAttachedFilesCount = 0;
        for (let i = 0; i < fileList.length; i++) {
          const file = fileList.item(i);
          if (file) {
            if (
              SUPPORTED_FILE_EXTENSIONS.some((extension) =>
                file.name.endsWith(extension)
              )
            ) {
              newAttachedFilesCount++;
            }
          }
        }

        if (
          currentAttachedFilesCount + newAttachedFilesCount >
          MAX_ATTACHED_FILES
        ) {
          open(
            t('error.attachment.fileCountExceeded', {
              maxCount: MAX_ATTACHED_FILES,
            })
          );
          return;
        }

        for (let i = 0; i < fileList.length; i++) {
          const file = fileList.item(i);
          if (file) {
            if (
              SUPPORTED_FILE_EXTENSIONS.some((extension) =>
                file.name.endsWith(extension)
              )
            ) {
              handleAttachedFileRead(file);
            } else if (
              acceptMediaType.some((extension) => file.name.endsWith(extension))
            ) {
              encodeAndPushImage(file);
            } else {
              open(t('error.unsupportedFileFormat'));
            }
          }
        }
      },
      [encodeAndPushImage, handleAttachedFileRead, open, t, acceptMediaType]
    );

    const onDragOver: React.DragEventHandler<HTMLDivElement> = useCallback(
      (e) => {
        e.preventDefault();
      },
      []
    );

    const onDrop: React.DragEventHandler<HTMLDivElement> = useCallback(
      (e) => {
        e.preventDefault();
        onChangeFile(e.dataTransfer.files);
      },
      [onChangeFile]
    );

    return (
      <>
        {props.dndMode && (
          <div
            className="fixed left-0 top-0 size-full bg-black/40"
            onDrop={onDrop}></div>
        )}
        <div
          ref={inputRef}
          onDragOver={onDragOver}
          onDrop={onDrop}
          className={twMerge(
            props.className,
            'relative mb-7 flex w-11/12 flex-col gap-1 rounded-xl border border-black/10 bg-white shadow-[0_0_30px_7px] shadow-light-gray dark:bg-aws-ui-color-dark dark:shadow-black/35 md:w-10/12 lg:w-4/6 xl:w-3/6'
          )}>
          <div className="flex w-full">
            <Textarea
              key={`textarea-${props.isNewChat}`} // Add a key to force re-render
              className="m-1 bg-transparent pr-12 scrollbar-thin scrollbar-thumb-light-gray"
              placeholder={t('app.inputMessage')}
              disabled={props.disabled}
              noBorder
              rows={props.isNewChat ? 3 : 1}
              value={content}
              onChange={setContent}
              ref={focusInputRef}
            />
          </div>
          <div className="bottom-0 right-0 flex w-full items-center justify-between px-2">
            <div className="flex">
              <ButtonFileChoose
                disabled={props.isLoading}
                icon
                accept={extendedAcceptMediaType.join(',')}
                onChange={onChangeFile}>
                <LuFilePlus2 />
              </ButtonFileChoose>
              {props.supportReasoning && (
                <ButtonReasoning
                  disabled={props.isLoading || props.canContinue}
                  showReasoning={reasoningEnabled}
                  forceReasoningEnabled={forceReasoningEnabled}
                  onToggleReasoning={() => onChangeReasoning(!reasoningEnabled)}
                />
              )}
            </div>
            <ButtonSend
              className="m-2 align-bottom"
              disabled={disabledSend || props.disabled}
              loading={props.isLoading}
              onClick={sendContent}
            />
          </div>
          {base64EncodedImages.length > 0 && (
            <div className="relative m-2 mr-24 flex flex-wrap gap-3">
              {base64EncodedImages.map((imageFile, idx) => (
                <div key={idx} className="relative">
                  <img
                    src={imageFile}
                    className="h-16 rounded border border-aws-squid-ink-light dark:border-aws-squid-ink-dark"
                    onClick={() => {
                      setPreviewImageUrl(imageFile);
                      setIsOpenPreviewImage(true);
                    }}
                  />
                  <ButtonIcon
                    className="absolute left-0 top-0 -m-2 border border-aws-sea-blue-light bg-white p-1 text-xs text-aws-sea-blue-light dark:border-aws-sea-blue-dark dark:text-aws-sea-blue-dark"
                    onClick={() => {
                      removeBase64EncodedImage(idx);
                    }}>
                    <PiX />
                  </ButtonIcon>
                </div>
              ))}
              <ModalDialog
                isOpen={isOpenPreviewImage}
                onClose={() => setIsOpenPreviewImage(false)}
                // Set image null after transition end
                onAfterLeave={() => setPreviewImageUrl(null)}
                widthFromContent={true}>
                {previewImageUrl && (
                  <img
                    src={previewImageUrl}
                    className="mx-auto max-h-[80vh] max-w-full rounded-md"
                  />
                )}
              </ModalDialog>
            </div>
          )}
          {(attachedFiles.length > 0 || s3AttachedFiles.length > 0) && (
            <div className="relative m-2 mr-24 flex flex-wrap gap-3">
              {attachedFiles.map((file, idx) => (
                <div key={`regular-${idx}`} className="relative flex flex-col items-center">
                  <UploadedAttachedFile fileName={file.name} />
                  <ButtonIcon
                    className="absolute left-2 top-1 -m-2 border border-aws-sea-blue-light bg-white p-1 text-xs text-aws-sea-blue-light dark:border-aws-sea-blue-dark dark:text-aws-sea-blue-dark"
                    onClick={() => {
                      removeTextFile(idx);
                    }}>
                    <PiX />
                  </ButtonIcon>
                </div>
              ))}
              {s3AttachedFiles.map((file, idx) => (
                <div key={`s3-${idx}`} className="relative flex flex-col items-center">
                  <UploadedAttachedFile fileName={`${file.name} (S3)`} />
                  <ButtonIcon
                    className="absolute left-2 top-1 -m-2 border border-aws-sea-blue-light bg-white p-1 text-xs text-aws-sea-blue-light dark:border-aws-sea-blue-dark dark:text-aws-sea-blue-dark"
                    onClick={() => {
                      removeS3File(idx);
                    }}>
                    <PiX />
                  </ButtonIcon>
                </div>
              ))}
            </div>
          )}
          {props.canRegenerate && (
            <div className="absolute -top-14 right-0 flex space-x-2">
              {props.canContinue &&
                !props.disabledContinue &&
                !props.disabled && (
                  <Button
                    className="bg-aws-paper-light p-2 text-sm dark:bg-aws-paper-dark"
                    outlined
                    onClick={props.continueGenerate}>
                    <PiArrowFatLineRight className="mr-2" />
                    {t('button.continue')}
                  </Button>
                )}
              <Button
                className="bg-aws-paper-light p-2 text-sm dark:bg-aws-paper-dark"
                outlined
                disabled={props.disabledRegenerate || props.disabled}
                onClick={() => {
                  props.onRegenerate(reasoningEnabled);
                }}>
                <PiArrowsCounterClockwise className="mr-2" />
                {t('button.regenerate')}
              </Button>
            </div>
          )}
        </div>
      </>
    );
  }
);

export default InputChatContent;
