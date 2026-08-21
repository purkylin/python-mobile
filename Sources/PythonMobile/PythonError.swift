import Foundation

public enum PythonError: LocalizedError, Sendable {
    case runtimeUnavailable(String)
    case initializationFailed(String)
    case executionFailed(String)
    case invalidResponse(String)

    public var errorDescription: String? {
        switch self {
        case .runtimeUnavailable(let msg):
            return "Python runtime unavailable: \(msg)"
        case .initializationFailed(let msg):
            return "Python initialization failed: \(msg)"
        case .executionFailed(let msg):
            return "Python execution error: \(msg)"
        case .invalidResponse(let msg):
            return "Invalid Python response: \(msg)"
        }
    }
}
