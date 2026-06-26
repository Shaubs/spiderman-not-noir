// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::process::{Command as StdCommand, Stdio};
use std::sync::Mutex;
use std::thread;
use tauri::{AppHandle, Emitter, Manager, State};

// Shared state for the Python process
struct PythonState {
    running: Mutex<bool>,
}

// Detection data structure
#[derive(Clone, serde::Serialize)]
struct DetectionPayload {
    #[serde(rename = "type")]
    msg_type: String,
    data: serde_json::Value,
}

#[tauri::command]
fn start_detector(app: AppHandle, state: State<PythonState>) -> Result<String, String> {
    let mut running = state.running.lock().map_err(|e| e.to_string())?;
    
    if *running {
        return Ok("Detector already running".to_string());
    }
    
    *running = true;
    
    // In dev mode, use the source path directly
    // In production, this would be in the resource directory
    let python_path = if cfg!(debug_assertions) {
        // Dev mode - use source directory
        std::env::current_dir()
            .map_err(|e| e.to_string())?
            .parent()
            .ok_or("No parent dir")?
            .join("python")
            .join("detector.py")
    } else {
        // Production - use resource directory
        app.path()
            .resource_dir()
            .map_err(|e| e.to_string())?
            .join("python")
            .join("detector.py")
    };
    
    let python_path_str = python_path.to_string_lossy().to_string();
    eprintln!("Starting Python detector: {}", python_path_str);
    
    // Clone app handle for the thread
    let app_clone = app.clone();
    
    // Spawn Python process in a separate thread
    thread::spawn(move || {
        // Use system Python with our detector script
        let mut child = match StdCommand::new("python3")
            .arg(&python_path_str)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
        {
            Ok(c) => c,
            Err(e) => {
                eprintln!("Failed to start Python: {}", e);
                let _ = app_clone.emit("error", format!("Failed to start detector: {}", e));
                return;
            }
        };
        
        // Read stdout line by line (JSON-L format)
        if let Some(stdout) = child.stdout.take() {
            let reader = BufReader::new(stdout);
            for line in reader.lines() {
                match line {
                    Ok(json_line) => {
                        // Parse JSON and emit event to frontend
                        if let Ok(data) = serde_json::from_str::<serde_json::Value>(&json_line) {
                            let msg_type = data.get("type")
                                .and_then(|t| t.as_str())
                                .unwrap_or("unknown")
                                .to_string();
                            
                            let _ = app_clone.emit(&msg_type, data);
                        }
                    }
                    Err(e) => {
                        eprintln!("Error reading Python output: {}", e);
                        break;
                    }
                }
            }
        }
        
        let _ = child.wait();
    });
    
    Ok("Detector started".to_string())
}

#[tauri::command]
fn stop_detector(state: State<PythonState>) -> Result<String, String> {
    let mut running = state.running.lock().map_err(|e| e.to_string())?;
    *running = false;
    // Note: In production, we'd send a shutdown signal to Python
    Ok("Detector stopped".to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(PythonState {
            running: Mutex::new(false),
        })
        .invoke_handler(tauri::generate_handler![start_detector, stop_detector])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
