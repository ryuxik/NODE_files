// Author: Ondrej Cierny 
#ifndef __LOG
#define __LOG

#include <iostream>
#include <iomanip>

// Variable argument logging function with clock timestamp
//-----------------------------------------------------------------------------
template<typename... args>
void log(std::ostream& stream, args&&... msgs)
//-----------------------------------------------------------------------------
{
	using expand = int[];
	stream << "[" << std::fixed << std::setprecision(2) << (float)clock()/CLOCKS_PER_SEC << std::setprecision(5) << "] ";
	expand{0, (void(stream << std::forward<args>(msgs) << " "), 0)...};
	stream << std::endl;
}

// Confirmable standard C-output version
//-----------------------------------------------------------------------------
template<typename... args>
void logAndConfirm(args&&... msgs)
//-----------------------------------------------------------------------------
{
	using expand = int[];
	std::cout << "[" << std::fixed << std::setprecision(2) << (float)clock()/CLOCKS_PER_SEC << std::setprecision(5) << "] ";
	expand{0, (void(std::cout << std::forward<args>(msgs) << " "), 0)...};
	std::cin.ignore();
}

#endif
