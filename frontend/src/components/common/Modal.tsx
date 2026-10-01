import { useEffect, useCallback, useState, type ReactNode } from 'react'
import { X } from 'lucide-react'
import './Modal.css'

type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | 'full'

interface ModalProps {
  /** Whether the modal is visible */
  open: boolean
  /** Called when close is requested (X button, overlay click, Escape) */
  onClose: () => void
  /** Modal title */
  title?: ReactNode
  /** Footer content (typically action buttons) */
  footer?: ReactNode
  /** Modal width */
  size?: ModalSize
  /** Whether clicking overlay closes the modal */
  closeOnOverlay?: boolean
  /** Whether pressing Escape closes the modal */
  closeOnEscape?: boolean
  children?: ReactNode
}

export default function Modal({
  open,
  onClose,
  title,
  footer,
  size = 'md',
  closeOnOverlay = true,
  closeOnEscape = true,
  children,
}: ModalProps) {
  const [closing, setClosing] = useState(false)

  const handleClose = useCallback(() => {
    setClosing(true)
    setTimeout(() => {
      setClosing(false)
      onClose()
    }, 150) // match fade-out duration
  }, [onClose])

  // Escape key handler
  useEffect(() => {
    if (!open || !closeOnEscape) return

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose()
    }

    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, closeOnEscape, handleClose])

  // Lock body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [open])

  if (!open && !closing) return null

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (closeOnOverlay && e.target === e.currentTarget) {
      handleClose()
    }
  }

  return (
    <div
      className={`modal-overlay ${closing ? 'modal-overlay--closing' : ''}`}
      onClick={handleOverlayClick}
      role="dialog"
      aria-modal="true"
    >
      <div className={`modal modal--${size}`}>
        {/* Header */}
        {(title || true) && (
          <div className="modal__header">
            <div className="modal__title">{title}</div>
            <button
              className="modal__close"
              onClick={handleClose}
              aria-label="Close modal"
              title="Close"
            >
              <X size={18} />
            </button>
          </div>
        )}

        {/* Body */}
        <div className="modal__body">{children}</div>

        {/* Footer */}
        {footer && <div className="modal__footer">{footer}</div>}
      </div>
    </div>
  )
}
