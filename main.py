"""
LED Animation Playback Engine - Terminal Mode
High-performance LED animation system with OSC control
"""

import asyncio
import sys
import argparse
import signal
import os
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.core.animation_engine import AnimationEngine
from config.settings import EngineSettings
from src.utils.logger import setup_logger, LoggerMode
from src.utils.performance import PerformanceMonitor

logger = None
app_instance = None


class LEDEngineApp:
    """
    Main LED Animation Engine Application
    Handles initialization, execution, and cleanup of the LED animation system
    """
    
    def __init__(self, verbose: bool = False):
        global logger
        
        self.verbose = verbose
        self.engine = None
        self.running = False
        self.performance_monitor = PerformanceMonitor()
        
        LoggerMode.set_mode(LoggerMode.TERMINAL)
        
        if self.verbose:
            os.environ['LOG_LEVEL'] = 'DEBUG'
        
        logger = setup_logger(__name__)
        
        logger.info("LED Animation Engine - Terminal Mode")
        logger.info(f"Target: {EngineSettings.ANIMATION.target_fps} FPS, {EngineSettings.ANIMATION.led_count} LEDs")
        logger.info(f"OSC: {EngineSettings.OSC.input_host}:{EngineSettings.OSC.input_port}")
    
    async def initialize(self):
        """
        Initialize the animation engine and all subsystems
        """
        global logger
        try:
            logger.info("Starting LED Animation Engine...")
            
            start_time = time.time()
            
            self.engine = AnimationEngine()
            await self.engine.start()
            
            initialization_time = time.time() - start_time
            logger.info(f"Engine initialized in {initialization_time:.2f}s")
            
            self.running = True
            
            logger.info("LED Animation Engine started successfully")
            logger.info("Ready for OSC commands. Press Ctrl+C to stop")
            
        except Exception as e:
            if logger:
                logger.error(f"Initialization failed: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                print(f"FATAL ERROR: {e}", file=sys.stderr, flush=True)
            await self.cleanup()
            sys.exit(1)
    
    async def run(self):
        """
        Main execution loop for terminal mode
        Monitors engine status and logs periodic statistics
        """
        logger.info("Starting main execution loop...")
        
        status_log_interval = 300  # 5 phút
        performance_log_interval = 600  # 10 phút
        last_status_log = 0
        last_performance_log = 0
        
        try:
            while self.running:
                current_time = time.time()
                
                if current_time - last_status_log >= status_log_interval:
                    await self._log_status()
                    last_status_log = current_time
                
                if current_time - last_performance_log >= performance_log_interval:
                    await self._log_performance()
                    last_performance_log = current_time
                
                await asyncio.sleep(5)  # Check mỗi 5 giây thay vì 1 giây
                    
        except KeyboardInterrupt:
            logger.info("Received stop signal (Ctrl+C)")
            self.running = False
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.running = False
        
        await self.cleanup()
    
    async def _log_status(self):
        """
        Log current engine status
        """
        try:
            stats = self.engine.get_stats()
            scene_info = self.engine.get_scene_info()
            
            logger.info("=" * 40)
            logger.info("ENGINE STATUS")
            logger.info("=" * 40)
            logger.info(f"Runtime: {stats.animation_time:.1f}s")
            logger.info(f"FPS: {stats.actual_fps:.1f}/{stats.target_fps}")
            logger.info(f"Frames: {stats.frame_count}")
            logger.info(f"Active LEDs: {stats.active_leds}/{stats.total_leds}")
            logger.info(f"Scene: {scene_info.get('scene_id', 'None')}")
            logger.info(f"Effect: {scene_info.get('effect_id', 'None')}")
            logger.info(f"Palette: {scene_info.get('palette_id', 'None')}")
            logger.info(f"Brightness: {stats.master_brightness}/255")
            logger.info(f"Speed: {stats.speed_percent}%")
            
            if stats.actual_fps < stats.target_fps * 0.9:
                logger.warning(f"Performance warning: FPS below target ({stats.actual_fps:.1f} < {stats.target_fps})")
            
        except Exception as e:
            logger.error(f"Error logging status: {e}")
    
    async def _log_performance(self):
        """
        Log detailed performance metrics
        """
        try:
            stats = self.engine.get_stats()
            osc_stats = self.engine.osc_handler.get_stats()
            led_stats = self.engine.led_output.get_stats()
            
            logger.info("=" * 50)
            logger.info("PERFORMANCE METRICS")
            logger.info("=" * 50)
            logger.info(f"Animation FPS: {stats.actual_fps:.2f}")
            logger.info(f"Total Frames: {stats.frame_count}")
            logger.info(f"OSC Messages: {osc_stats['message_count']}")
            logger.info(f"OSC Errors: {osc_stats['error_count']}")
            logger.info(f"LED Sends: {led_stats['send_count']}")
            logger.info(f"LED Errors: {led_stats['error_count']}")
            logger.info(f"LED Output FPS: {led_stats.get('actual_send_fps', 0):.2f}")
            logger.info(f"Active Devices: {led_stats['active_devices']}/{led_stats['total_devices']}")
            
            efficiency = (stats.actual_fps / stats.target_fps) * 100 if stats.target_fps > 0 else 0
            logger.info(f"Engine Efficiency: {efficiency:.1f}%")
            
        except Exception as e:
            logger.error(f"Error logging performance: {e}")
    
    async def cleanup(self):
        """
        Clean up all resources and stop the engine
        """
        logger.info("=" * 40)
        logger.info("SHUTTING DOWN ENGINE")
        logger.info("=" * 40)
        
        self.running = False
        
        if self.engine:
            try:
                final_stats = self.engine.get_stats()
                logger.info(f"Final runtime: {final_stats.animation_time:.1f}s")
                logger.info(f"Total frames processed: {final_stats.frame_count}")
                logger.info(f"Average FPS: {final_stats.actual_fps:.1f}")
                
                await self.engine.stop()
                logger.info("Animation Engine stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping engine: {e}")
        
        logger.info("Cleanup completed")
        logger.info("=" * 40)


def signal_handler(signum, frame):
    """
    Handle system signals for graceful shutdown
    """
    global app_instance
    print("\nReceived shutdown signal, stopping engine...", flush=True)
    if app_instance:
        app_instance.running = False


async def run_terminal():
    """
    Run engine in terminal mode
    """
    global app_instance
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    app_instance = LEDEngineApp(verbose=args.verbose if 'args' in globals() else False)
    await app_instance.initialize()
    await app_instance.run()


def print_banner():
    """
    Print application banner
    """
    print("LED Animation Engine")
    print(f"Target: {EngineSettings.ANIMATION.target_fps} FPS | LEDs: {EngineSettings.ANIMATION.led_count}")
    print()


def main():
    """
    Main entry point for the LED Animation Engine
    """
    global args
    
    print_banner()
    
    parser = argparse.ArgumentParser(
        description='LED Animation Playback Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run with default settings
  python main.py --verbose         # Run with debug logging
  python main.py --config custom   # Use custom configuration
  
OSC Control:
  /load_json "path/to/scenes.json"  # Load animation scenes
  /change_scene 1                   # Switch to scene 1
  /change_effect 2                  # Switch to effect 2
  /change_palette A                 # Switch to palette A
  /master_brightness 128            # Set brightness to 50%
        """
    )
    
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true',
        help='Enable verbose debug logging'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Custom configuration file path'
    )
    
    parser.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='Run as daemon process'
    )
    
    args = parser.parse_args()
    
    if args.config:
        print(f"Using configuration: {args.config}")
    
    if args.verbose:
        print("Verbose logging enabled")
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    if args.daemon:
        print("Running in daemon mode...")
    
    try:
        asyncio.run(run_terminal())
    except KeyboardInterrupt:
        print("\nEngine stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("LED Animation Engine terminated")


if __name__ == "__main__":
    main()