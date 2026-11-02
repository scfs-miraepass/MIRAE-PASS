interface ResponsePayload {
    success: boolean
}

export interface ResponseModel<T> extends ResponsePayload {
    data: T
}

export interface ErrorResponse extends ResponsePayload {
    message: string
}

export type Result<T> =
    | { success: true; data: T }
    | { success: false; message: string };